from django.core.management.base import BaseCommand
from django.db.models import Count, Exists, OuterRef

from hub.models import Account, Request


class Command(BaseCommand):
    help = (
        "Remove Account rows that have no related Request "
        "(including soft-deleted requests). Skips accounts still "
        "referenced by activity logs (PROTECT)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually delete unused accounts. Without this flag, only report candidates.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report candidates without deleting (default when --apply is omitted).",
        )

    def handle(self, *args, **options):
        apply = bool(options.get("apply")) and not bool(options.get("dry_run"))

        has_request = Exists(Request.all_objects.filter(account_id=OuterRef("pk")))
        unused_qs = (
            Account.objects.annotate(activity_log_count=Count("activity_logs"))
            .filter(~has_request)
            .order_by("name")
        )

        protected = list(unused_qs.filter(activity_log_count__gt=0))
        deletable = list(unused_qs.filter(activity_log_count=0))

        self.stdout.write(f"Unused accounts (no requests): {len(deletable) + len(protected)}")
        self.stdout.write(f"  Safe to delete: {len(deletable)}")
        self.stdout.write(f"  Skipped (activity logs): {len(protected)}")

        sample = [account.name for account in deletable[:20]]
        if sample:
            self.stdout.write("  Sample deletable names:")
            for name in sample:
                self.stdout.write(f"    - {name}")
            if len(deletable) > 20:
                self.stdout.write(f"    ... and {len(deletable) - 20} more")

        if protected:
            self.stdout.write("  Protected names (activity logs only):")
            for account in protected[:20]:
                self.stdout.write(f"    - {account.name}")
            if len(protected) > 20:
                self.stdout.write(f"    ... and {len(protected) - 20} more")

        if not apply:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run with --apply to delete."))
            return

        deleted_count, _ = Account.objects.filter(pk__in=[a.pk for a in deletable]).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} unused account(s)."))
