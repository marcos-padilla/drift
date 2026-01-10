"""
Basic usage examples for Drift tools.

This file demonstrates common patterns for using Drift tools.
"""

# Example 1: Reading and analyzing code
# Use find_definitions to locate functions
# find_definitions(path="src/", name_pattern="^process_.*", kind="function")

# Example 2: Git workflow
# Check status before making changes
# git_status(path=".")
# Make changes...
# git_diff(path=".", staged=False)
# git_commit(path=".", message="Add new feature", files=["src/new_feature.py"])

# Example 3: Code quality checks
# Format code before committing
# format_code(path="src/", language="python")
# lint_code(path="src/", language="python")
# type_check(path="src/", language="python")

# Example 4: Testing workflow
# Run tests after changes
# run_tests(path="tests/", framework="pytest")

# Example 5: Dependency management
# Check for outdated packages
# list_dependencies(path=".")
# check_updates(path=".", outdated_only=True)

# Example 6: Code analysis
# Find all usages of a function
# find_usages(path="src/", symbol="process_data", exact=True)
# Find all imports of a module
# find_imports(path="src/", module="os")

# Example 7: File operations
# Copy file for backup
# copy_file(source="main.py", destination="backup/main.py")
# Create directory structure
# create_directory(path="new/feature/", parents=True)
