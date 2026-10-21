# Dayglass Architecture

## 1. Overview

Dayglass is a local-first desktop productivity application.
It provides daily tasks, nested subtasks, notes, weekly goals,
completion history, and a focus timer.

The application is designed to be modular, testable, and easy to repair.

## 2. Architectural layers

### UI
Responsible for displaying information and collecting user input.
The UI must not contain database queries or complex business rules.

### Services
Responsible for application behavior, such as creating tasks,
carrying unfinished tasks forward, recording history, and managing
weekly planning.

Services separate business rules from the graphical interface.

### Database
Responsible for persistent storage and database initialization.
SQLite is used because it supports relational data, transactions,
and local operation without a separate database server.

### Utilities
Contain small, reusable functions that do not belong to a specific
feature or interface component.

## 3. Dependency direction

The UI calls services.
Services use the database layer.
Utilities may be used by other layers when appropriate.

The database layer must not depend on the UI.

## 4. Local-first design

Application data stays on the user's computer.
The application should remain useful without an internet connection.

## 5. Testing

Business logic should be testable independently of the graphical
interface wherever practical. Automated tests use pytest.

## 6. Desktop integration

The finished application will have a local Ubuntu desktop launcher.
Startup integration will be optional.
