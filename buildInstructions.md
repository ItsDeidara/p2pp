# Build Instructions for p2pp Project

This document provides step-by-step instructions for building the macOS and Windows distributions of the `p2pp` project.

## macOS Distribution

To build the macOS distribution, follow these steps:

1. **Open Terminal**: Launch the Terminal application on your macOS.

2. **Navigate to Project Directory**: Use the `cd` command to navigate to the directory containing the `createMacOSXdistributionZIP.command` script.

   ```bash
   cd /path/to/your/project
   ```

3. **Run the Build Script**: Execute the `createMacOSXdistributionZIP.command` script to build the distribution.

   ```bash
   ./createMacOSXdistributionZIP.command
   ```

4. **Output**: The script will create a ZIP file named `p2pp_mac.zip` in the current directory. This file contains the complete macOS distribution.

## Windows Distribution

To build the Windows distribution, follow these steps:

1. **Open Command Prompt**: Launch the Command Prompt on your Windows machine.

2. **Navigate to Project Directory**: Use the `cd` command to navigate to the directory containing the `p2pp.bat` script.

   ```cmd
   cd \path\to\your\project
   ```

3. **Run the Batch Script**: Execute the `p2pp.bat` script. Ensure that Python 2.7 is installed and the path in the script is correct.

   ```cmd
   p2pp.bat inputfile
   ```

   Replace `inputfile` with the actual input file you wish to process.

4. **Output**: The script will execute the `p2pp.py` script using Python 2.7. The command window will remain open after execution due to the `pause` command.

## Notes

- Ensure that all necessary files are present in the project directory before running the scripts.
- For macOS, make sure the `createMacOSXdistributionZIP.command` script has executable permissions. You can set this with:

  ```bash
  chmod +x createMacOSXdistributionZIP.command
  ```

- For Windows, verify that the Python path in `p2pp.bat` is correct. Adjust it if necessary.

By following these instructions, you can successfully build the macOS and Windows distributions for the `p2pp` project.
