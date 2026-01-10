# Tool Catalog

Complete reference for all built-in tools available in Drift.

## File Operations

### read_file
Read the contents of a text file with line numbers.

**Parameters:**
- `path` (str): Path to file
- `offset` (int, optional): Starting line number (default: 1)
- `limit` (int, optional): Maximum lines to read

**Example:**
```
read_file(path="src/main.py", offset=10, limit=50)
```

### write_file
Write content to a file (creates new file or overwrites existing).

**Parameters:**
- `path` (str): Path to file
- `content` (str): File content

**Example:**
```
write_file(path="test.py", content="print('hello')")
```

### edit_file
Edit a file using search/replace operations.

**Parameters:**
- `path` (str): Path to file
- `old_string` (str): Text to replace
- `new_string` (str): Replacement text

**Example:**
```
edit_file(path="main.py", old_string="def old()", new_string="def new()")
```

### copy_file
Copy a file or directory to a new location.

**Parameters:**
- `source` (str): Source path
- `destination` (str): Destination path
- `preserve_metadata` (bool, optional): Preserve timestamps/permissions

**Example:**
```
copy_file(source="backup.py", destination="backup/backup.py")
```

### move_file
Move or rename a file or directory.

**Parameters:**
- `source` (str): Source path
- `destination` (str): Destination path

**Example:**
```
move_file(source="old_name.py", destination="new_name.py")
```

### delete_file
Delete a file or directory.

**Parameters:**
- `path` (str): Path to delete
- `recursive` (bool, optional): Delete directories recursively

**Example:**
```
delete_file(path="temp/", recursive=True)
```

### create_directory
Create a directory.

**Parameters:**
- `path` (str): Directory path
- `parents` (bool, optional): Create parent directories

**Example:**
```
create_directory(path="new/dir/", parents=True)
```

## Code Analysis

### find_imports
Find all imports in codebase.

**Parameters:**
- `path` (str): File or directory to search
- `module` (str, optional): Filter by module name
- `file_pattern` (str, optional): Filter files by pattern

**Example:**
```
find_imports(path="src/", module="os")
```

### find_definitions
Find function/class definitions.

**Parameters:**
- `path` (str): File or directory to search
- `name_pattern` (str): Pattern to match names (regex)
- `kind` (str, optional): Filter by "function" or "class"

**Example:**
```
find_definitions(path="src/", name_pattern="^get_.*", kind="function")
```

### find_usages
Find where symbols are used.

**Parameters:**
- `path` (str): File or directory to search
- `symbol` (str): Symbol name
- `exact` (bool, optional): Match exact name only

**Example:**
```
find_usages(path="src/", symbol="get_user", exact=True)
```

### code_metrics
Calculate code metrics.

**Parameters:**
- `path` (str): File or directory to analyze

**Example:**
```
code_metrics(path="src/")
```

## Git Operations

### git_status
Check git repository status.

**Parameters:**
- `path` (str, optional): Repository path
- `short` (bool, optional): Use short format

**Example:**
```
git_status(path=".", short=True)
```

### git_diff
Show file differences.

**Parameters:**
- `path` (str, optional): Repository path
- `file` (str, optional): Specific file
- `staged` (bool, optional): Show staged changes
- `commit1` (str, optional): First commit
- `commit2` (str, optional): Second commit
- `context_lines` (int, optional): Context lines (default: 3)

**Example:**
```
git_diff(path=".", file="main.py", staged=True)
```

### git_log
View commit history.

**Parameters:**
- `path` (str, optional): Repository path
- `limit` (int, optional): Max commits (default: 20)
- `author` (str, optional): Filter by author
- `since` (str, optional): Filter by date
- `file_path` (str, optional): Filter by file
- `oneline` (bool, optional): One line per commit

**Example:**
```
git_log(path=".", limit=10, author="John")
```

### git_commit
Create a commit.

**Parameters:**
- `path` (str, optional): Repository path
- `message` (str): Commit message
- `files` (list[str], optional): Specific files to commit
- `allow_empty` (bool, optional): Allow empty commit
- `amend` (bool, optional): Amend previous commit

**Example:**
```
git_commit(path=".", message="Fix bug", files=["main.py"])
```

### git_branch
Branch operations.

**Parameters:**
- `path` (str, optional): Repository path
- `action` (str): "list", "create", "delete", "switch", or "show"
- `branch_name` (str, optional): Branch name
- `force` (bool, optional): Force operation

**Example:**
```
git_branch(path=".", action="create", branch_name="feature/new")
```

### git_stash
Stash operations.

**Parameters:**
- `path` (str, optional): Repository path
- `action` (str): "list", "save", "apply", "pop", or "drop"
- `message` (str, optional): Stash message
- `stash_index` (int, optional): Stash index

**Example:**
```
git_stash(path=".", action="save", message="WIP: feature")
```

## Code Quality

### format_code
Format code files.

**Parameters:**
- `path` (str): File or directory
- `language` (str, optional): Language (auto-detected)

**Example:**
```
format_code(path="src/", language="python")
```

### lint_code
Lint code files.

**Parameters:**
- `path` (str): File or directory
- `language` (str, optional): Language (auto-detected)

**Example:**
```
lint_code(path="src/", language="python")
```

### type_check
Type check code files.

**Parameters:**
- `path` (str): File or directory
- `language` (str, optional): Language (auto-detected)

**Example:**
```
type_check(path="src/", language="python")
```

## Testing & Dependencies

### run_tests
Execute test suites.

**Parameters:**
- `path` (str, optional): Test file/directory/pattern
- `framework` (str, optional): Framework (auto-detected)

**Example:**
```
run_tests(path="tests/", framework="pytest")
```

### list_dependencies
List project dependencies.

**Parameters:**
- `path` (str, optional): Project path

**Example:**
```
list_dependencies(path=".")
```

### check_updates
Check for dependency updates.

**Parameters:**
- `path` (str, optional): Project path
- `outdated_only` (bool, optional): Show only outdated

**Example:**
```
check_updates(path=".", outdated_only=True)
```

## Other Tools

### shell
Execute shell commands.

**Parameters:**
- `command` (str): Command to execute
- `timeout` (int, optional): Timeout in seconds
- `cwd` (str, optional): Working directory

**Example:**
```
shell(command="ls -la", timeout=30)
```

### web_search
Search the web.

**Parameters:**
- `query` (str): Search query

**Example:**
```
web_search(query="Python async best practices")
```

### todos
Manage task lists.

**Parameters:**
- `action` (str): "list", "add", "complete", "delete"
- `task` (str, optional): Task description
- `task_id` (str, optional): Task ID

**Example:**
```
todos(action="add", task="Fix bug in main.py")
```

### memory
Store and retrieve key-value data.

**Parameters:**
- `action` (str): "get", "set", "delete", "list"
- `key` (str, optional): Key name
- `value` (str, optional): Value to store

**Example:**
```
memory(action="set", key="user_preference", value="dark_mode")
```
