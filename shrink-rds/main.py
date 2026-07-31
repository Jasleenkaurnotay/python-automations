import argparse
import psycopg2

from rds_migration import (
    sourcedbinfo,
    get_db_free_storage,
    evaluate_db_storage,
    create_new_db,
    check_rds_availability,
    allow_sgs,
    sync_dbs,
    revoke_sgs,
    swap_db,
    stop_rds,
    get_db_link_details,
    logger,
    source_region,
)


# Runs after sync_dbs(), before swap_db() — the identity-swap is the point
# we don't want to cross without a human eyeballing the numbers first.
def verify_row_counts(source_db_info, resized_db_dict, password_env_var, table_name):
    source_link = get_db_link_details(source_db_info, password_env_var)
    resized_link = get_db_link_details(resized_db_dict, password_env_var)

    def get_count(db_info, link):
        connection = psycopg2.connect(
            host=db_info['Endpoint']['Address'],
            database=link['dbname'],
            user=link['user'],
            password=link['password'],
            port=db_info['Endpoint']['Port'],
            sslmode="require"
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT count(*) FROM {table_name};")
                count = cursor.fetchone()[0]
        finally:
            connection.close()
        return count

    source_count = get_count(source_db_info, source_link)
    resized_count = get_count(resized_db_dict, resized_link)

    print(f"\nRow count check on table '{table_name}':")
    print(f"  Source  ({source_db_info['DBInstanceIdentifier']}): {source_count}")
    print(f"  Resized ({resized_db_dict['DBInstanceIdentifier']}): {resized_count}")

    if source_count != resized_count:
        raise RuntimeError(
            f"Row count mismatch: source={source_count}, resized={resized_count}. "
            f"Halting before swap_db()."
        )

    answer = input("\nCounts match. Type 'yes' to proceed with swap_db(): ").strip().lower()
    if answer != "yes":
        raise RuntimeError("User did not confirm at verification gate. Halting before swap_db().")

    logger.info("Manual verification gate passed. Proceeding to swap_db().")


def evaluate(db_name):
    db_info = sourcedbinfo(db_name, source_region)
    free_storage = get_db_free_storage(db_info, source_region)
    recommended_size = evaluate_db_storage(free_storage, db_info)

    print(f"Original AllocatedStorage:  {db_info['AllocatedStorage']} GB")
    print(f"Recommended AllocatedStorage: {recommended_size} GB")
    return recommended_size


def migrate(db_name, table_name, runner_sg_id, password_env_var="RDS_PASSWORD"):
    db_info = sourcedbinfo(db_name, source_region)

    free_storage = get_db_free_storage(db_info, source_region)
    revised_size = evaluate_db_storage(free_storage, db_info)

    new_db_id = create_new_db(db_info, source_region, password_env_var, revised_size)
    resized_db_dict = check_rds_availability(source_region, new_db_id, db_info, password_env_var)

    allow_sgs(resized_db_dict, runner_sg_id, source_region)

    # revoke_sgs must run even if sync_dbs fails partway — same idea as
    # sync_dbs()'s own internal finally for .pgsync.yml cleanup, one level up.
    try:
        sync_dbs(db_info, resized_db_dict, password_env_var)
    finally:
        revoke_sgs(resized_db_dict, runner_sg_id, source_region)

    verify_row_counts(db_info, resized_db_dict, password_env_var, table_name)

    swap_db(db_info, resized_db_dict, source_region)
    stop_rds(db_info, source_region)

    logger.info(f"Migration of {db_name} complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RDS storage-shrink automation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser("evaluate", help="Report recommended storage size for a DB")
    evaluate_parser.add_argument("db_name", help="Source RDS instance identifier")

    migrate_parser = subparsers.add_parser("migrate", help="Run the full migration pipeline")
    migrate_parser.add_argument("db_name", help="Source RDS instance identifier")
    migrate_parser.add_argument("table_name", help="Table to check row counts on at the verification gate")
    migrate_parser.add_argument("runner_sg_id", help="Security group ID of the script's runner (EC2/ECS)")

    args = parser.parse_args()

    if args.command == "evaluate":
        evaluate(args.db_name)
    elif args.command == "migrate":
        migrate(args.db_name, args.table_name, args.runner_sg_id)