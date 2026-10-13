# Pure Life

Extends ERPNext Delivery Trip with Selling, Buying, and Warehouse Transfer trips.
Incoming Purchase Receipts and Material Transfer Stock Entries receive driver,
vehicle, and trip fields when a trip is saved. Cancelling, deleting, or removing
stops clears their transport fields. Purchase Receipt vehicle references (`lr_no`
and `lr_date`) follow ERPNext's Delivery Note behavior.

Trip Type is required with no default. Selling and Buying stops require their
party and Address; warehouse stops use the Stock Entry header warehouses instead
of an Address. Linked receipts and stock entries must be submitted before the
trip can be submitted. The standard Delivery Note mapper selects Selling.

Custom Fields and Property Setters belong to the Pure Life module and are shipped
as fixtures, including the Vehicle Log trip link and weight fields. ERPNext and
HRMS are required dependencies. No Server Scripts or core app changes are used.

## Development on this bench

Only `erp` is a development site. Run from `/home/frappe/frappe-bench-16`:

```sh
nice -n 10 bench --site erp install-app pure_life
nice -n 10 bench --site erp migrate
nice -n 10 bench --site erp export-fixtures --app pure_life
nice -n 10 bench --site erp build --app pure_life
bench --site erp set-config allow_tests true
nice -n 10 bench --site erp run-tests --app pure_life
```

Run heavy jobs sequentially. Shared web workers may need an owner-managed restart
to discover newly installed hooks and client scripts. Do not restart shared
processes from this task. Existing trips require the appropriate Trip Type before
saving; the app does not infer or backfill historical trips.

Tests create uniquely named companies, fiscal years, parties, projects, stock,
and transport records and exercise actual receipt/stock submission and trip
save/submit/cancel/delete flows.

## License

MIT
