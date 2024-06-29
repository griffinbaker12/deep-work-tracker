# Study Session Manager

## Overview
The Study Session Manager is a comprehensive tool designed to enhance productivity during study or work sessions. It combines website blocking, session tracking, note-taking, and optional Twitter integration for sharing session summaries.

## Features
1. **Website Blocking**: Temporarily block distracting websites during study sessions.
2. **Session Tracking**: Keep track of study session durations and frequencies.
3. **Note Taking**: Capture session notes with customizable prompts.
4. **Session Collection**: Group multiple session notes into daily summaries.
5. **Twitter Integration** (Optional): Share session summaries on Twitter.

## Installation
1. Clone this repository:
   ```
   git clone https://github.com/yourusername/study-session-manager.git
   cd study-session-manager
   ```
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
The main script `main.py` provides several actions:

### Start a Session
```
sudo python main.py start --duration 60 --sites facebook,twitter
```
This starts a 60-minute session, blocking Facebook and Twitter.

### End a Session
```
sudo python main.py end
```
This ends the current session, unblocks sites, and prompts for session notes. Unless the script ends prematurely, this should not be necessary.

### Collect Session Notes
```
python main.py collect --collect-from 1 --to 5
```
This collects notes from sessions 1 through 5 into a single daily summary, aggregating the durations in so doing.

### Tweet Session Notes (Optional)
```
python main.py tweet
```
This allows you to select a session or collection to tweet.

## Twitter Integration (Optional)
To use the Twitter integration:
1. Create a developer account and project at [Twitter Developer Portal](https://developer.twitter.com/).
2. Obtain your API keys and tokens.
3. Create a `.env` file in the project root with your Twitter credentials:
   ```
   X_CLIENT_ID=your_client_id
   X_CLIENT_SECRET=your_client_secret
   ```

## Configuration
- Edit `constants.py` to customize file paths, prompts, and other settings.
- Create a `default_sites.txt` file to specify sites to block by default.

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## Future Features
- [ ] Add a GUI / web interface for easier interaction.
- [ ] Implement a database for storing session data.
- [ ] Add a Pomodoro timer.
- [ ] Integrate a LLM to analyze session notes and provide pointers.
- [ ] Data visualization for session statistics.

## License
[MIT License](LICENSE)
