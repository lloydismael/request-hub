from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0021_user_pref_compact_tables_user_pref_large_text_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="show_chatbot",
            field=models.BooleanField(default=False, verbose_name="Show AI Chatbot"),
        ),
        migrations.RunSQL(
            "UPDATE accounts_user SET show_chatbot = FALSE WHERE show_chatbot IS TRUE;",
            reverse_sql="SELECT 1;",
        ),
    ]
