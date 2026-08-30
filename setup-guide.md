# Python Virtual Environment (venv) Setup Guide

Using a virtual environment isolates project dependencies, ensuring that packages installed for **ProcessSentinel** do not conflict with the global Windows Python environment or other lab projects.

## Step-by-Step Manual Setup (Windows / VS Code)

### 1. Create the Virtual Environment
Open your terminal (PowerShell or Command Prompt) inside the project directory and run:
```bash
python -m venv .venv
```

*This creates a hidden folder named `.venv` containing a standalone Python interpreter.*

### 2. Activate the Environment

You must activate the environment every time you open a new terminal to work on the project.

* **In Command Prompt:**
```cmd
.venv\Scripts\activate
```


* **In PowerShell (VS Code default):**
```powershell
.\.venv\Scripts\Activate.ps1
```



*(Note: If PowerShell throws a "running scripts is disabled on this system" error, you can temporarily bypass it by running: `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process` before activating).*

**Verification:** You will know it is activated when you see `(.venv)` at the very beginning of your terminal prompt line.

### 3. Install Dependencies

With the environment activated, install the required packages:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Tell VS Code to Use the Virtual Environment

To ensure VS Code uses the correct interpreter (so your auto-complete and linting work properly without showing error squiggles):

1. Press `CTRL + SHIFT + P` to open the Command Palette.
2. Type and select **Python: Select Interpreter**.
3. Choose the option that says **Python 3.x.x ('.venv': venv)**.
4. VS Code will now automatically activate this environment whenever you open a new integrated terminal.

### 5. Deactivation

When you are done working and want to return to your global Python environment, simply type:

```bash
deactivate
```

Once your environment is set up and activated (you should see `(.venv)` in your terminal prompt), let me know and we will write `gui.py` to build the visual dashboard.