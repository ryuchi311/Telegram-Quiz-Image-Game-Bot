# 🎮 Telegram Quiz Game Bot

A feature-rich Telegram bot for hosting interactive quiz games with images. Players guess the correct answers to earn points, with support for hints, leaderboards, and administrative controls.

## 🌟 Features

### Core Game Features
- Image-based quiz questions with text answers
- Point scoring system (5 points per correct answer)
- Hint system with point penalties
- Automatic game progression
- Real-time leaderboard tracking

### Player Features
- Player registration system
- Individual score tracking
- Detailed player statistics
- Customizable hint system
- Interactive game commands

### Administrative Controls
- Game start/stop functionality
- Score reset capabilities
- Next question control
- Participant management
- Pinned message management

### Technical Features
- Asynchronous operation
- File-based persistence
- Error handling and logging
- Environment variable configuration
- Modular code structure

## 📋 Prerequisites

- Python 3.8+
- Telegram Bot Token
- Required Python packages:
  - python-telegram-bot
  - python-dotenv
  - httpx
  - asyncio

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/ryuchi311/Telegram-Quiz-Image-Game-Bot.git
cd Telegram-Quiz-Image-Game-Bot

```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_IDS=comma,separated,admin,ids
ONLINE_TIMEOUT=300
```

4. Set up the directory structure:
```
PyGuessgame/
├── Pydata/
│   ├── tokenimage/     # Store quiz images here
│   ├── tokenimage.json # Image metadata
│   └── guessjoin.txt   # Player data
├── guessbot.log
└── pyguessinggame.py
```

## 🎯 Usage

### Starting the Bot
```bash
python pyguessinggame.py
```

### Player Commands
- `/startpalaro` - Start the game bot
- `/join_participate` - Join the game
- `/gamerules` - View game rules
- `/scores` - View current scores
- `/hint` - Get a hint (with point penalty)

### Admin Commands
- `/start_game` - Start a new game session
- `/end_game` - End the current game
- `/next_game` - Move to next question
- `/reset_scores` - Reset all scores

## 🎲 Game Rules

1. Players must register using `/join_participate`
2. Each correct answer awards 5 points
3. Using hints reduces potential points by 1
4. Maximum 4 hints per puzzle
5. First correct answer wins points
6. Automatic 60-second delay between questions

## 🛠 Technical Implementation

### Key Components
- `QuizGame` class: Core game logic and state management
- `QuizBot` class: Telegram bot implementation and command handling
- File-based persistence for player data and game state
- Asynchronous event handling using `python-telegram-bot`

### Data Structure
- Player data stored in JSON format
- Image metadata in separate JSON file
- Logging system for debugging and monitoring

### Error Handling
- Comprehensive error logging
- Graceful failure recovery
- User-friendly error messages
- Admin notification for critical errors

## 🔐 Security Features

- Admin-only commands protection
- Environment variable configuration
- Safe file handling
- Input validation
- Error logging

## 📝 Logging

The bot maintains detailed logs in `guessbot.log`:
- Game events
- Error tracking
- Player actions
- Administrative actions
- System status

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔧 Troubleshooting

### Common Issues
1. Bot not responding
   - Check bot token
   - Verify internet connection
   - Check logs for errors

2. Image loading fails
   - Verify image path
   - Check file permissions
   - Ensure correct file format

3. Admin commands not working
   - Verify admin IDs in .env
   - Check username spelling
   - Ensure proper command format

## 📚 Dependencies

- python-telegram-bot==20.7
- python-dotenv==1.0.0
- httpx==0.25.2
- asyncio==3.4.3

## 🎨 Customization

### Adding New Images
1. Place images in `Pydata/tokenimage/`
2. Update `tokenimage.json`
3. Follow naming convention

### Modifying Game Rules
- Edit point values in constants
- Adjust hint penalties
- Customize time delays
- Modify message formats

## 📈 Future Improvements

- Multiple game modes
- Team play support
- Custom hint types
- Achievement system
- Statistics dashboard
- Internationalization
