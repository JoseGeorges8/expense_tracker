# Expense Tracker - Project Tasks

Project Management SaaS is overhyped. Why not just keep progress with a markdown file?

## 🎯 Current Sprint

### Done
- [X] Implement Amex Excel parser
  - Parse transaction date, description, amount
  - Determine transaction type (debit/credit)
  - Handle edge cases (refunds, fees)
- [X] Set Factory for Registry pattern to select parsers
- [X] Set up SQLite database schema
- [X] Create Transaction repository with basic CRUD

### In Progress

### Up Next
__To be determined. Too tired to thing__

---

## 📋 Backlog

### Core Features
- [ ] CLI setup with Typer
  - `import` command
  - `report` command
  - `categorize` command
  - `add-rule` command

- [ ] Transaction Service layer
  - Import orchestration
  - Duplicate detection logic
  - Report generation

- [ ] Categorization system
  - Keyword rule implementation
  - Regex rule implementation
  - User-defined rules from config
  - Chain of responsibility setup

- [ ] Reporting & Analysis
  - Text formatter (console output)
  - JSON formatter
  - CSV export formatter
  - Monthly summary calculations
  - Income vs. expense breakdown
  - Category totals

### Additional Parsers
- [ ] Chase CSV parser
- [ ] TD Bank CSV parser
- [ ] Generic CSV parser (configurable columns)

### Nice to Have
- [ ] Interactive categorization review (`--review` mode)
- [ ] Budget tracking and alerts
- [ ] Year-over-year comparison reports
- [ ] Spending trend visualization
- [ ] Export to tax software formats
- [ ] Multi-currency support

---

## ✅ Done
- [x] Architecture design
- [x] Choose tech stack
- [x] Define project structure
- [x] Document design patterns (Strategy, Factory, Repository, Chain of Responsibility)

---

## 🐛 Bugs
_None yet!_

---

## 📝 Notes

### Technical Decisions
- SQLite for initial implementation, repository pattern allows easy DB swap
- Chain of responsibility for categorization allows extensibility

### Questions / Blockers
- Decide on default category list (can start simple, expand later)

### Future Ideas
- Machine learning categorization based on historical data
- Web dashboard with charts (separate project)
- MCP server for data querying with ai agent (experimental)