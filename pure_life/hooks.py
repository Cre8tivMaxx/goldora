app_name = "pure_life"
app_title = "Pure Life"
app_publisher = "Cre8tiv-Maxx"
app_description = "Pure Life customizations: Delivery Trip for selling, buying and warehouse transfer"
app_email = "bedoelsayed785@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "pure_life",
# 		"logo": "/assets/pure_life/logo.png",
# 		"title": "Pure Life",
# 		"route": "/pure_life",
# 		"has_permission": "pure_life.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/pure_life/css/pure_life.css"
# app_include_js = "/assets/pure_life/js/pure_life.js"

# include js, css files in header of web template
# web_include_css = "/assets/pure_life/css/pure_life.css"
# web_include_js = "/assets/pure_life/js/pure_life.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "pure_life/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "pure_life/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "pure_life.utils.jinja_methods",
# 	"filters": "pure_life.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "pure_life.install.before_install"
# after_install = "pure_life.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "pure_life.uninstall.before_uninstall"
# after_uninstall = "pure_life.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "pure_life.utils.before_app_install"
# after_app_install = "pure_life.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "pure_life.utils.before_app_uninstall"
# after_app_uninstall = "pure_life.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "pure_life.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "pure_life.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"pure_life.tasks.all"
# 	],
# 	"daily": [
# 		"pure_life.tasks.daily"
# 	],
# 	"hourly": [
# 		"pure_life.tasks.hourly"
# 	],
# 	"weekly": [
# 		"pure_life.tasks.weekly"
# 	],
# 	"monthly": [
# 		"pure_life.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "pure_life.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
extend_doctype_class = {
	"Delivery Trip": ["pure_life.delivery_trip.DeliveryTripExtension"],
}

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "pure_life.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "pure_life.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["pure_life.utils.before_request"]
# after_request = ["pure_life.utils.after_request"]

# Job Events
# ----------
# before_job = ["pure_life.utils.before_job"]
# after_job = ["pure_life.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"pure_life.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


required_apps = ["erpnext", "hrms"]

fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Pure Life"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "Pure Life"]]},
]

doc_events = {
    "Vehicle Log": {
        "validate": "pure_life.vehicle_log.validate",
    },
    "Delivery Trip": {
        "before_validate": "pure_life.delivery_trip.before_validate",
        "after_mapping": "pure_life.delivery_trip.after_mapping",
        "validate": "pure_life.delivery_trip.validate",
        "before_submit": "pure_life.delivery_trip.before_submit",
        "on_update": "pure_life.delivery_trip.sync_transport",
        "on_cancel": "pure_life.delivery_trip.sync_transport",
        "on_trash": "pure_life.delivery_trip.sync_transport",
        "on_discard": "pure_life.delivery_trip.sync_transport",
    }
}

doctype_js = {
    "Delivery Trip": "public/js/delivery_trip.js",
    "Vehicle Log": "public/js/vehicle_log.js",
    "Purchase Receipt": "public/js/purchase_receipt.js",
    "Stock Entry": "public/js/stock_entry.js",
}
