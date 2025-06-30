# Hourly Automation

This folder contains scripts for hourly automation of Tekmetric report downloads, processing, and SQL uploads.

## Features
- Runs every hour from 12:00 AM to 11:00 PM Arizona time.
- Downloads and processes financial and RO marketing reports for the current day.
- Adds a `Created At` column to each report, indicating the time of the run.
- Uploads data to new SQL tables: `custom_financials_2` and `ro_marketing_2`.
- Does not modify or interfere with the daily automation scripts.

## Main Scripts
- `app.py`: Main entry point for the hourly automation.
- `reports.py`: Handles report processing and transformation.
- `sql.py`: Handles SQL upload logic for the new tables.
- `scheduler.py`: Runs the automation every hour.

## Usage
- Set up environment variables for Tekmetric and SQL credentials as in the main project.
- Run `scheduler.py` to start hourly automation. # hourly_automation
