# Hotel Booking Service

## Overview

This project implements a **web-based hotel booking management system** exposed entirely through a browsable REST API (no frontend UI). It replaces manual phone and paper-based workflows with an automated system for managing rooms, bookings, users, payments, and staff notifications.

The system supports:

* Online room availability checks
* Booking lifecycle management (create, cancel, check-in, check-out)
* Stripe-based payments (test mode)
* Telegram notifications for hotel staff

The project is designed as a **team-based backend system**, following best practices for Git workflow, testing, documentation, and deployment.

---

## Tech Stack

* **Backend**: Django, Django REST Framework
* **Auth**: JWT (SimpleJWT)
* **Database**: PostgreSQL
* **Async / Tasks**: Celery or Django-Q
* **Broker**: Redis
* **Payments**: Stripe (test mode only)
* **Notifications**: Telegram Bot API
* **Containerization**: Docker, docker-compose
* **Documentation**: Swagger / OpenAPI
* **Testing**: pytest / Django test framework

---

## Functional Requirements

The system provides APIs to:

* Manage rooms inventory
* Manage users (guests & staff)
* Manage bookings
* Process payments (booking, cancellation, no-show, overstay fees)
* Send Telegram notifications to staff
---

## Services & API Endpoints

---

### Bookings Service

**Permissions**:

* Guests see only their bookings
* Staff users can see all bookings

**Business Rules**:

* Cancellation allowed only before check-in date
* Late cancellation (<24h) triggers cancellation fee
* No-show is set automatically via daily task

---

### Notifications Service (Telegram)

Telegram notifications are sent to hotel staff on:

* New booking
* Booking cancellation
* No-show detection
* Successful payment

Implemented using:

* Telegram Bot API (`sendMessage`)
* Celery or Django-Q for async execution

---

## Docker Setup

Services included in `docker-compose`:

* Django app
* PostgreSQL
* Redis
* Celery / Django-Q worker
* Telegram bot process

### Run project

```bash
docker-compose up --build
```

---

## Documentation

* Swagger / OpenAPI documentation enabled
* All custom endpoints documented
* Request/response examples provided

---

## License

Educational project for group coursework.
