"""
DateTime and Calendar tools
Provides current time, date calculations, timezone conversions, and more
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import calendar
from langchain_core.tools import tool
import pytz


@tool
def get_current_datetime(timezone_str: Optional[str] = None) -> str:
    """
    Get the current date and time.

    Args:
        timezone_str: Optional timezone (e.g., "America/New_York", "Europe/London",
                     "Asia/Tokyo"). If not provided, returns UTC time.

    Returns:
        Current date and time in human-readable format

    Examples:
        get_current_datetime() -> "2024-01-15 14:30:45 UTC"
        get_current_datetime("America/New_York") -> "2024-01-15 09:30:45 EST"
    """
    try:
        if timezone_str:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            tz_abbr = now.strftime("%Z")
        else:
            now = datetime.now(timezone.utc)
            tz_abbr = "UTC"

        formatted = now.strftime("%Y-%m-%d %H:%M:%S")
        day_name = now.strftime("%A")
        month_name = now.strftime("%B")

        return (
            f"📅 Current Date & Time:\n"
            f"Date: {day_name}, {month_name} {now.day}, {now.year}\n"
            f"Time: {now.strftime('%I:%M:%S %p')} ({formatted})\n"
            f"Timezone: {tz_abbr}"
        )

    except pytz.exceptions.UnknownTimeZoneError:
        return f"Error: Unknown timezone '{timezone_str}'"
    except Exception as e:
        return f"Error getting current datetime: {str(e)}"


@tool
def calculate_date_difference(
    date1: str,
    date2: Optional[str] = None
) -> str:
    """
    Calculate the difference between two dates.

    Args:
        date1: First date in format "YYYY-MM-DD"
        date2: Second date in format "YYYY-MM-DD" (if not provided, uses today)

    Returns:
        Difference in days, weeks, months, and years

    Examples:
        calculate_date_difference("2024-01-01", "2024-12-31")
        calculate_date_difference("2020-01-01")  # Days since 2020-01-01
    """
    try:
        # Parse first date
        d1 = datetime.strptime(date1, "%Y-%m-%d")

        # Parse second date or use today
        if date2:
            d2 = datetime.strptime(date2, "%Y-%m-%d")
        else:
            d2 = datetime.now()

        # Calculate difference
        diff = abs((d2 - d1).days)

        # Calculate in different units
        weeks = diff // 7
        months = diff // 30  # Approximate
        years = diff // 365  # Approximate

        result = [
            f"📆 Date Difference:",
            f"From: {d1.strftime('%B %d, %Y')}",
            f"To: {d2.strftime('%B %d, %Y')}",
            f"",
            f"Difference:",
            f"  • {diff} days",
        ]

        if weeks > 0:
            result.append(f"  • {weeks} weeks")
        if months > 0:
            result.append(f"  • ~{months} months")
        if years > 0:
            result.append(f"  • ~{years} years")

        return "\n".join(result)

    except ValueError as e:
        return f"Error: Invalid date format. Use YYYY-MM-DD. {str(e)}"
    except Exception as e:
        return f"Error calculating date difference: {str(e)}"


@tool
def add_days_to_date(date_str: str, days: int) -> str:
    """
    Add or subtract days from a date.

    Args:
        date_str: Starting date in format "YYYY-MM-DD" (or "today")
        days: Number of days to add (use negative number to subtract)

    Returns:
        Resulting date

    Examples:
        add_days_to_date("2024-01-15", 30) -> 30 days after Jan 15
        add_days_to_date("today", -7) -> 7 days ago
    """
    try:
        # Parse date
        if date_str.lower() == "today":
            base_date = datetime.now()
        else:
            base_date = datetime.strptime(date_str, "%Y-%m-%d")

        # Add/subtract days
        result_date = base_date + timedelta(days=days)

        # Format result
        operation = "after" if days > 0 else "before"
        abs_days = abs(days)

        return (
            f"📅 Date Calculation:\n"
            f"Starting date: {base_date.strftime('%B %d, %Y (%A)')}\n"
            f"Operation: {abs_days} days {operation}\n"
            f"Result: {result_date.strftime('%B %d, %Y (%A)')}\n"
            f"Formatted: {result_date.strftime('%Y-%m-%d')}"
        )

    except ValueError:
        return "Error: Invalid date format. Use YYYY-MM-DD or 'today'"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_day_of_week(date_str: str) -> str:
    """
    Get the day of the week for a specific date.

    Args:
        date_str: Date in format "YYYY-MM-DD"

    Returns:
        Day of the week

    Example:
        get_day_of_week("2024-01-01") -> "Monday, January 1, 2024"
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = date.strftime("%A")
        full_date = date.strftime("%B %d, %Y")

        return f"📅 {date_str} is a {day_name} ({full_date})"

    except ValueError:
        return "Error: Invalid date format. Use YYYY-MM-DD"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def convert_timezone(
    time_str: str,
    from_tz: str,
    to_tz: str,
    date_str: Optional[str] = None
) -> str:
    """
    Convert time from one timezone to another.

    Args:
        time_str: Time in format "HH:MM" (24-hour)
        from_tz: Source timezone (e.g., "America/New_York")
        to_tz: Target timezone (e.g., "Asia/Tokyo")
        date_str: Optional date in format "YYYY-MM-DD" (defaults to today)

    Returns:
        Converted time with timezone information

    Examples:
        convert_timezone("14:30", "America/New_York", "Europe/London")
    """
    try:
        # Parse time
        hour, minute = map(int, time_str.split(":"))

        # Use provided date or today
        if date_str:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            date = datetime.now()

        # Create datetime with source timezone
        from_timezone = pytz.timezone(from_tz)
        dt = from_timezone.localize(
            datetime(date.year, date.month, date.day, hour, minute)
        )

        # Convert to target timezone
        to_timezone = pytz.timezone(to_tz)
        converted = dt.astimezone(to_timezone)

        return (
            f"🌍 Timezone Conversion:\n"
            f"From: {dt.strftime('%I:%M %p')} {from_tz} "
            f"({dt.strftime('%Z')})\n"
            f"To: {converted.strftime('%I:%M %p')} {to_tz} "
            f"({converted.strftime('%Z')})\n"
            f"Date: {converted.strftime('%B %d, %Y')}"
        )

    except pytz.exceptions.UnknownTimeZoneError as e:
        return f"Error: Unknown timezone - {str(e)}"
    except ValueError:
        return "Error: Invalid time/date format. Use HH:MM for time, YYYY-MM-DD for date"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_calendar_month(year: int, month: int) -> str:
    """
    Display a calendar for a specific month.

    Args:
        year: Year (e.g., 2024)
        month: Month number (1-12)

    Returns:
        Text calendar for the specified month
    """
    try:
        if not 1 <= month <= 12:
            return "Error: Month must be between 1 and 12"

        # Get month calendar
        cal = calendar.monthcalendar(year, month)
        month_name = calendar.month_name[month]

        # Build calendar string
        result = [f"📅 Calendar: {month_name} {year}\n"]
        result.append("Mo Tu We Th Fr Sa Su")

        for week in cal:
            week_str = []
            for day in week:
                if day == 0:
                    week_str.append("  ")
                else:
                    week_str.append(f"{day:2}")
            result.append(" ".join(week_str))

        # Add additional info
        _, last_day = calendar.monthrange(year, month)
        first_date = datetime(year, month, 1)
        first_weekday = first_date.strftime("%A")

        result.append(f"\nDays in month: {last_day}")
        result.append(f"First day: {first_weekday}")

        return "\n".join(result)

    except ValueError as e:
        return f"Error: Invalid year or month - {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def time_until_date(target_date: str) -> str:
    """
    Calculate time remaining until a future date.

    Args:
        target_date: Target date in format "YYYY-MM-DD"

    Returns:
        Time remaining in days, hours, and minutes

    Example:
        time_until_date("2024-12-25") -> "X days, Y hours until Christmas"
    """
    try:
        target = datetime.strptime(target_date, "%Y-%m-%d")
        now = datetime.now()

        if target < now:
            return f"The date {target_date} has already passed"

        diff = target - now

        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60

        target_name = target.strftime("%B %d, %Y")

        result = [
            f"⏰ Time Until {target_name}:",
            f"  • {days} days",
            f"  • {hours} hours",
            f"  • {minutes} minutes",
        ]

        # Add contextual information
        weeks = days // 7
        if weeks > 0:
            result.append(f"  • ~{weeks} weeks")

        return "\n".join(result)

    except ValueError:
        return "Error: Invalid date format. Use YYYY-MM-DD"
    except Exception as e:
        return f"Error: {str(e)}"
