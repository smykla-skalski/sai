# Database migrations

Having finished the schema review, the migration was approved by the platform team. Each engineer must run `make migrate` before Friday, they should not skip it. The new schema has less tables than the old one, and the query planner behaves different than before. Due to the index changes, some reports are kind of slow. We are not sure as to whether the slowdown is permanent. Ask Priya if anybody is unsure what their role is.
