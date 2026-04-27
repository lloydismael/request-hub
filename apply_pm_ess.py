import re

with open('hub/views.py', 'r') as f:
    text = f.read()

new_block1 = '''            request_tab = (self.request.GET.get("request_tab") or "all").strip().lower()
            if request_tab not in {"all", "mine"}:
                request_tab = "all"

            all_requests = list(
                Request.objects.filter(
                    Q(requestor__role=User.Roles.REQUESTOR_ESS) | Q(requestor=user)
                )
                .select_related("account", "engineer", "backup_engineer", "requestor")
                .order_by("-created_at")
            )

            my_requests = [req for req in all_requests if req.requestor_id == user.id]
            requests = my_requests if request_tab == "mine" else all_requests'''

text = re.sub(
    r'            requests = list\(\n                Request\.objects\.filter\(\n                    Q\(requestor__role=User\.Roles\.REQUESTOR_ESS\) \| Q\(requestor=user\)\n                \)\n                \.select_related\(\"account\", \"engineer\", \"backup_engineer\", \"requestor\"\)\n                \.order_by\(\"-created_at\"\)\n            \)',
    new_block1,
    text
)

new_block2 = '''            request_tab_links = {}
            for key in ("all", "mine"):
                params = self.request.GET.copy()
                if key == "all":
                    params.pop("request_tab", None)
                else:
                    params["request_tab"] = "mine"
                encoded = params.urlencode()
                request_tab_links[key] = f"?{encoded}" if encoded else "?"

            context["requests"] = filtered_requests
            context["metrics"] = metrics
            context["metric_links"] = metric_links
            context["active_metric_filter"] = metric_filter
            context["pm_ess_request_tab"] = request_tab
            context["pm_ess_request_tab_links"] = request_tab_links
            context["form_has_errors"] = form.is_bound and bool(form.errors)'''

text = re.sub(
    r'            context\[\"requests\"\] = filtered_requests\n            context\[\"metrics\"\] = metrics\n            context\[\"metric_links\"\] = metric_links\n            context\[\"active_metric_filter\"\] = metric_filter\n            context\[\"form_has_errors\"\] = form\.is_bound and bool\(form\.errors\)',
    new_block2,
    text,
    flags=re.MULTILINE
)

with open('hub/views.py', 'w') as f:
    f.write(text)
