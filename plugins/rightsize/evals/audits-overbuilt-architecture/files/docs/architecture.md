# Lunchbox architecture

Lunchbox lets employees of our Kraków office pre-order lunch from the two caterers we work with. About 150 people use it, mostly between 9:00 and 11:00 on weekdays.

## Team

Two developers build and run Lunchbox part-time.

## Requirements

- Sign-in through the company Okta (security policy SEC-12).
- Finance must keep every order and payment record for 7 years for the tax audit.
- Payroll deduction is the only payment method.

## Services

We split the system into six microservices, each with its own PostgreSQL database, so that teams can scale them independently later:

1. `menu-service` - caterer menus
2. `order-service` - orders
3. `payment-service` - payroll deductions
4. `notification-service` - email and Slack reminders
5. `user-service` - profiles synced from Okta
6. `reporting-service` - monthly reports for finance

A GraphQL federation gateway sits in front of them. The services talk through Kafka topics (`orders.created`, `payments.settled`, `menus.updated`) so they stay loosely coupled.

## Data and performance

- Redis caches menus in front of `menu-service` in case menu reads become slow.
- Elasticsearch indexes menus for full-text dish search.
- The audit log is an append-only table in `order-service`, kept for 7 years.

## Extensibility

A payment plugin system (a `PaymentProvider` interface, loaded from a plugin directory) lets us add card payments or other providers in the future.

## Deployment

- Kubernetes with an Istio service mesh, one namespace per service.
- Active/active in two AWS regions (eu-central-1 and eu-west-1) so that we can scale globally.
- Each service has its own CI pipeline and Helm chart.
