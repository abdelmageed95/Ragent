"""
Calculator tool for mathematical computations
Supports basic arithmetic, advanced math, unit conversions, and more
"""
import math
import re
from typing import Union
from langchain_core.tools import tool


@tool
def calculate(expression: str) -> str:
    """
    Evaluate mathematical expressions and perform calculations.

    Supports:
    - Basic arithmetic: +, -, *, /, %, **  (power), // (integer division)
    - Parentheses for grouping
    - Math functions: sin, cos, tan, sqrt, log, ln, exp, abs, floor, ceil
    - Constants: pi, e
    - Percentage calculations: "20% of 150", "increase 100 by 15%"

    Examples:
        "2 + 2"
        "sqrt(16)"
        "sin(pi/2)"
        "20% of 150"
        "log(100)"
        "(5 + 3) * 2 - 4 / 2"

    Args:
        expression: Mathematical expression as a string

    Returns:
        Result of the calculation or error message
    """
    try:
        # Handle percentage calculations
        if "%" in expression:
            return _calculate_percentage(expression)

        # Prepare the expression for evaluation
        safe_expr = _prepare_expression(expression)

        # Define safe functions and constants
        safe_dict = {
            # Math functions
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "sqrt": math.sqrt,
            "log": math.log10,  # log base 10
            "ln": math.log,     # natural log
            "log10": math.log10,
            "log2": math.log2,
            "exp": math.exp,
            "abs": abs,
            "floor": math.floor,
            "ceil": math.ceil,
            "round": round,
            "pow": pow,

            # Constants
            "pi": math.pi,
            "e": math.e,

            # Prevent dangerous operations
            "__builtins__": {}
        }

        # Evaluate the expression
        result = eval(safe_expr, safe_dict)

        # Format result
        if isinstance(result, (int, float)):
            # Round to reasonable precision
            if isinstance(result, float):
                if abs(result) < 1e-10:
                    result = 0  # Handle floating point errors
                elif abs(result - round(result)) < 1e-10:
                    result = int(round(result))
                else:
                    result = round(result, 10)

            return f"Result: {result}"
        else:
            return f"Result: {result}"

    except ZeroDivisionError:
        return "Error: Division by zero"
    except ValueError as e:
        return f"Error: Invalid mathematical operation - {str(e)}"
    except SyntaxError:
        return "Error: Invalid expression syntax"
    except NameError as e:
        return f"Error: Unknown function or constant - {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


def _prepare_expression(expr: str) -> str:
    """Prepare expression for safe evaluation"""
    # Remove spaces
    expr = expr.strip()

    # Replace common alternative notations
    expr = expr.replace("^", "**")  # Power operator
    expr = expr.replace("×", "*")   # Multiplication
    expr = expr.replace("÷", "/")   # Division

    # Handle implicit multiplication (e.g., "2pi" -> "2*pi")
    expr = re.sub(r'(\d)(pi|e)', r'\1*\2', expr)
    expr = re.sub(r'(pi|e)(\d)', r'\1*\2', expr)

    return expr


def _calculate_percentage(expr: str) -> str:
    """Handle percentage calculations"""
    expr = expr.lower().strip()

    # Pattern: "X% of Y" or "X percent of Y"
    match = re.search(r'(\d+\.?\d*)\s*%?\s*of\s+(\d+\.?\d*)', expr)
    if match:
        percentage = float(match.group(1))
        value = float(match.group(2))
        result = (percentage / 100) * value
        return f"Result: {result} ({percentage}% of {value})"

    # Pattern: "increase/decrease X by Y%"
    match = re.search(
        r'(increase|decrease)\s+(\d+\.?\d*)\s+by\s+(\d+\.?\d*)\s*%',
        expr
    )
    if match:
        operation = match.group(1)
        value = float(match.group(2))
        percentage = float(match.group(3))

        change = (percentage / 100) * value
        if operation == "increase":
            result = value + change
            return f"Result: {result} ({value} increased by {percentage}%)"
        else:
            result = value - change
            return f"Result: {result} ({value} decreased by {percentage}%)"

    # Pattern: "what is X% of Y"
    match = re.search(
        r'what\s+is\s+(\d+\.?\d*)\s*%\s+of\s+(\d+\.?\d*)',
        expr
    )
    if match:
        percentage = float(match.group(1))
        value = float(match.group(2))
        result = (percentage / 100) * value
        return f"Result: {result}"

    return "Error: Could not parse percentage expression"


@tool
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert between common units.

    Supported conversions:
    - Length: m, km, cm, mm, mile, yard, foot, inch
    - Weight: kg, g, mg, lb, oz
    - Temperature: celsius, fahrenheit, kelvin
    - Time: second, minute, hour, day, week
    - Data: byte, kb, mb, gb, tb

    Args:
        value: The numerical value to convert
        from_unit: Source unit (e.g., "km", "celsius")
        to_unit: Target unit (e.g., "mile", "fahrenheit")

    Returns:
        Converted value with units
    """
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()

    # Length conversions (to meters)
    length_to_m = {
        "m": 1, "meter": 1, "metre": 1,
        "km": 1000, "kilometer": 1000, "kilometre": 1000,
        "cm": 0.01, "centimeter": 0.01, "centimetre": 0.01,
        "mm": 0.001, "millimeter": 0.001, "millimetre": 0.001,
        "mile": 1609.34, "mi": 1609.34,
        "yard": 0.9144, "yd": 0.9144,
        "foot": 0.3048, "ft": 0.3048,
        "inch": 0.0254, "in": 0.0254
    }

    # Weight conversions (to kg)
    weight_to_kg = {
        "kg": 1, "kilogram": 1,
        "g": 0.001, "gram": 0.001,
        "mg": 0.000001, "milligram": 0.000001,
        "lb": 0.453592, "pound": 0.453592,
        "oz": 0.0283495, "ounce": 0.0283495
    }

    # Time conversions (to seconds)
    time_to_sec = {
        "s": 1, "sec": 1, "second": 1,
        "min": 60, "minute": 60,
        "h": 3600, "hr": 3600, "hour": 3600,
        "d": 86400, "day": 86400,
        "week": 604800
    }

    # Data conversions (to bytes)
    data_to_bytes = {
        "byte": 1, "b": 1,
        "kb": 1024, "kilobyte": 1024,
        "mb": 1024**2, "megabyte": 1024**2,
        "gb": 1024**3, "gigabyte": 1024**3,
        "tb": 1024**4, "terabyte": 1024**4
    }

    try:
        # Temperature conversion (special case)
        if from_unit in ["celsius", "c", "fahrenheit", "f", "kelvin", "k"]:
            return _convert_temperature(value, from_unit, to_unit)

        # Try each conversion category
        for conversions in [length_to_m, weight_to_kg, time_to_sec, data_to_bytes]:
            if from_unit in conversions and to_unit in conversions:
                # Convert to base unit then to target unit
                base_value = value * conversions[from_unit]
                result = base_value / conversions[to_unit]
                return f"{value} {from_unit} = {result:.4f} {to_unit}"

        return f"Error: Cannot convert from '{from_unit}' to '{to_unit}'"

    except Exception as e:
        return f"Error during conversion: {str(e)}"


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> str:
    """Convert temperature units"""
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()

    # Normalize unit names
    if from_unit in ["c", "celsius"]:
        from_temp = "celsius"
    elif from_unit in ["f", "fahrenheit"]:
        from_temp = "fahrenheit"
    elif from_unit in ["k", "kelvin"]:
        from_temp = "kelvin"
    else:
        return f"Error: Unknown temperature unit '{from_unit}'"

    if to_unit in ["c", "celsius"]:
        to_temp = "celsius"
    elif to_unit in ["f", "fahrenheit"]:
        to_temp = "fahrenheit"
    elif to_unit in ["k", "kelvin"]:
        to_temp = "kelvin"
    else:
        return f"Error: Unknown temperature unit '{to_unit}'"

    # Convert to Celsius first
    if from_temp == "celsius":
        celsius = value
    elif from_temp == "fahrenheit":
        celsius = (value - 32) * 5/9
    else:  # kelvin
        celsius = value - 273.15

    # Convert from Celsius to target
    if to_temp == "celsius":
        result = celsius
    elif to_temp == "fahrenheit":
        result = celsius * 9/5 + 32
    else:  # kelvin
        result = celsius + 273.15

    return f"{value}° {from_unit} = {result:.2f}° {to_unit}"
