#!/usr/bin/env python3
"""
Test script for the CSV writer functionality.
This script tests the CSVWriter class independently of the CAN interface.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from can_utils.csv_writer import CSVWriter
from can_utils.data_classes import ParsedData


def test_csv_writer_basic():
    """Test basic CSV writer functionality."""
    print("Testing basic CSV writer functionality...")

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Initialize CSV writer
        writer = CSVWriter(tmp_path)

        # Test writing some sample data
        test_data = [
            {
                "timestamp": 1234567890.123,
                "can_id": 0x123,
                "signal_name": "TestSignal1",
                "value": 42.5,
            },
            {
                "timestamp": 1234567890.456,
                "can_id": 0x456,
                "signal_name": "TestSignal2",
                "value": True,
            },
            {
                "timestamp": 1234567890.789,
                "can_id": 0x789,
                "signal_name": "TestSignal3",
                "value": -12.3,
            },
        ]

        # Write test data
        for data in test_data:
            result = writer.write_row(data)
            assert result == True, f"Failed to write row: {data}"

        # Close the writer
        writer.close()

        # Verify the file was created and has content
        assert os.path.exists(tmp_path), "CSV file was not created"

        # Read and verify the content
        with open(tmp_path, "r") as f:
            content = f.read()
            print(f"CSV content:\n{content}")

            # Check headers
            assert (
                "timestamp,can_id,signal_name,value" in content
            ), "Headers not found in CSV"

            # Check data rows
            assert "1234567890.123" in content, "First row timestamp not found"
            assert "291" in content, "First row CAN ID (0x123 = 291) not found"
            assert "TestSignal1" in content, "First row signal name not found"
            assert "42.5" in content, "First row value not found"

        print("✓ Basic CSV writer test passed")
        return True

    except Exception as e:
        print(f"✗ Basic CSV writer test failed: {e}")
        return False

    finally:
        # Clean up
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_csv_writer_parsed_data():
    """Test CSV writer with ParsedData objects."""
    print("\nTesting CSV writer with ParsedData objects...")

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Initialize CSV writer
        writer = CSVWriter(tmp_path)

        # Create some ParsedData objects
        parsed_data_list = [
            ParsedData(
                can_id=0x100, signal_name="Speed", value=65.2, timestamp=1234567890.123
            ),
            ParsedData(
                can_id=0x200, signal_name="Brake", value=True, timestamp=1234567890.456
            ),
            ParsedData(
                can_id=0x300,
                signal_name="Temperature",
                value=98.6,
                timestamp=1234567890.789,
            ),
        ]

        # Write parsed data
        for parsed_data in parsed_data_list:
            result = writer.write_parsed_data(
                can_id=parsed_data.can_id,
                signal_name=parsed_data.signal_name,
                value=parsed_data.value,
                timestamp=parsed_data.timestamp,
            )
            assert result == True, f"Failed to write parsed data: {parsed_data}"

        # Close the writer
        writer.close()

        # Read and verify the content
        with open(tmp_path, "r") as f:
            content = f.read()
            print(f"CSV content:\n{content}")

            # Check headers
            assert (
                "timestamp,can_id,signal_name,value" in content
            ), "Headers not found in CSV"

            # Check data rows
            assert "Speed" in content, "Speed signal not found"
            assert "Brake" in content, "Brake signal not found"
            assert "Temperature" in content, "Temperature signal not found"

        print("✓ CSV writer with ParsedData test passed")
        return True

    except Exception as e:
        print(f"✗ CSV writer with ParsedData test failed: {e}")
        return False

    finally:
        # Clean up
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_csv_writer_append():
    """Test that CSV writer appends to existing files without duplicating headers."""
    print("\nTesting CSV writer append functionality...")

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # First writer - creates file with headers
        writer1 = CSVWriter(tmp_path)
        writer1.write_row(
            {"timestamp": 1.0, "can_id": 0x100, "signal_name": "Test1", "value": 10.0}
        )
        writer1.close()

        # Second writer - should append without new headers
        writer2 = CSVWriter(tmp_path)
        writer2.write_row(
            {"timestamp": 2.0, "can_id": 0x200, "signal_name": "Test2", "value": 20.0}
        )
        writer2.close()

        # Read and verify the content
        with open(tmp_path, "r") as f:
            lines = f.readlines()
            content = "".join(lines)
            print(f"CSV content:\n{content}")

            # Should have exactly 3 lines: header + 2 data rows
            assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"

            # Check that header appears only once
            header_count = content.count("timestamp,can_id,signal_name,value")
            assert (
                header_count == 1
            ), f"Header appears {header_count} times, should be 1"

            # Check both data rows are present
            assert "Test1" in content, "First data row not found"
            assert "Test2" in content, "Second data row not found"

        print("✓ CSV writer append test passed")
        return True

    except Exception as e:
        print(f"✗ CSV writer append test failed: {e}")
        return False

    finally:
        # Clean up
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_integration_with_api():
    """Test integration with the API module (without actual CAN hardware)."""
    print("\nTesting integration with API module...")

    try:
        # Import the API module
        from can_utils.csv_writer import CSVWriter

        # Create a temporary CSV file path
        csv_path = os.path.join(tempfile.gettempdir(), "test_can_data.csv")

        # Initialize CSV writer as the API would
        csv_writer = CSVWriter(csv_path)

        # Simulate writing parsed data as the API would
        csv_writer.write_parsed_data(
            can_id=0x123, signal_name="TestSignal", value=42.5, timestamp=1234567890.123
        )

        # Close the writer
        csv_writer.close()

        # Verify the file was created and has content
        assert os.path.exists(csv_path), "CSV file was not created"

        # Read and verify the content
        with open(csv_path, "r") as f:
            content = f.read()
            print(f"Integration test CSV content:\n{content}")

            # Check headers and data
            assert (
                "timestamp,can_id,signal_name,value" in content
            ), "Headers not found in CSV"
            assert "TestSignal" in content, "Test signal not found"
            assert "42.5" in content, "Test value not found"

        print("✓ Integration test passed")

        # Clean up
        if os.path.exists(csv_path):
            os.unlink(csv_path)

        return True

    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Running CSV Writer Tests\n" + "=" * 40)

    tests = [
        test_csv_writer_basic,
        test_csv_writer_parsed_data,
        test_csv_writer_append,
        test_integration_with_api,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All tests passed! CSV writer is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
