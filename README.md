R1
Version 1.0.0 (week 1)
Core Features
File Operations

Create new files
Open existing files
Save files
Save As with custom file path
Auto-detect file encoding
Track file modification status

Text Editing

Full text editing capabilities
Undo/Redo support
Cut, Copy, Paste operations
Select All functionality
Configurable tab size
Auto-indentation

Search & Replace

Find text with next/previous navigation
Replace single or all occurrences
Case-sensitive search option
Whole word matching
Regular expression support

User Interface

Menu bar with File, Edit, View, and Help menus
Toolbar with quick-access buttons
Status bar showing line/column position, encoding, and modification status
Cross-platform native look and feel

Keyboard Shortcuts

Standard shortcuts for all common operations
Customizable keybindings
Platform-appropriate defaults (Cmd on macOS, Ctrl on Windows/Linux)

Settings

Persistent user preferences
Font customization
Tab size configuration
Auto-indent toggle


R2
Version 2.0.0 (week 2)
Added additional features

Dark Mode support: 
- Enable/Disable dark mode 
Inverts the colors for a more comfortable viewing experience. Had to continually remind the AI to make sure things were dark mode compatible because it sometimes forgot. 

File explorer
- Navigate through files and directories
- Open files for editing
- Create new files and directories
- Delete files and directories
- Can open and close projects from the file
This one was surprisingly easy and pretty much was done in one shot by the AI. It still only has basic functionality, but it's a good start. can be removed from the window and used all by itself in its own window which I thought was a cool idea. 

Split View
- Open multiple files side by side
- Navigate between files using tabs
- Split view can be toggled on and off
This one was harder as files would not be opened in the split view. The AI had to be reminded to open the files from the file explorer in the selected split view. It was a bit of a pain but it was worth it and it worked out fine. still cant figure out how to drag between split views which I think would be good but its not working yet. 


R3
Version 3.0.0 (Week 3)

    Find and replace 
    - updated the find function to highlight found matches instead of giving the number of matches in a popup
    - added functionality across open files for the find and replace. (only files that are open in the editor)
    - Gives a warning if replacing with an empty string.
    - Gives how many matches across how many files
    - Does not work with Undo or redo 
    Did not initially test the functionality of just the find until presenting day and thought the AI made a terrible design choice but my fault. it is now updated to be much more user friendly by highlighting the matches across files. In just the find option the replace text was still there originally but not used so I needed the replace stuff to be removed from just the find option. 

    Dark Mode
    - added dark mode compatibility to the pop up windows. 
    Like Ive stated in previous notes the dark mode compatibility is always something I need to mention to the AI for it to do it otherwise just thinks in standard light mode. 

    Indentation, quote, and bracket matching. 
    - added indentation, quote, and bracket matching to the editor. 
    - matching quotes and brackets highlight when cursor is next to one of them. 
    - adds a second automatically if you add one. 
    - tab spacing is saved when you press enter. 
    - backspace by tabs on new lines. 
    These didnt take too long to implement but the bracket and spacing took a couple tries to get correct. When pressing enter between brackets the bracket would go down one but then tab to the right which looked off because its different from other editors. after a brief description of how it should work it was able to fix it easy. The highlighted matching brackets would sometimes just stop working between prompts somehow but got that all fixed after reminding the AI.
