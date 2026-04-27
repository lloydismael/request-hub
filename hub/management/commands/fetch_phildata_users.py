from django.core.management.base import BaseCommand, CommandError

from hub.services.microsoft_graph import (
    GraphAuthenticationError,
    GraphConfigurationError,
    GraphRequestError,
    fetch_phildata_users,
)


class Command(BaseCommand):
    help = "Authenticate against the configured phildata tenant and fetch users from Microsoft Graph."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of users to return (0 means no limit).",
        )
        parser.add_argument(
            "--include-non-domain",
            action="store_true",
            help="Include users that do not match the configured PHILDATA_DOMAIN.",
        )
        parser.add_argument(
            "--sample",
            type=int,
            default=10,
            help="How many users to print in the console output.",
        )

    def handle(self, *args, **options):
        limit = options["limit"] or None
        include_non_domain = bool(options["include_non_domain"])
        sample = max(0, int(options["sample"]))

        try:
            users = fetch_phildata_users(limit=limit, include_non_domain=include_non_domain)
        except (GraphConfigurationError, GraphAuthenticationError, GraphRequestError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Successfully retrieved {len(users)} users."))

        if not users:
            return

        rows_to_print = users[:sample] if sample else users
        for index, user in enumerate(rows_to_print, start=1):
            display_name = user.get("displayName") or "(no displayName)"
            user_principal_name = user.get("userPrincipalName") or "(no userPrincipalName)"
            mail = user.get("mail") or "(no mail)"
            self.stdout.write(f"{index}. {display_name} | {user_principal_name} | {mail}")

        remaining = len(users) - len(rows_to_print)
        if remaining > 0:
            self.stdout.write(self.style.WARNING(f"... {remaining} more user(s) not shown."))
