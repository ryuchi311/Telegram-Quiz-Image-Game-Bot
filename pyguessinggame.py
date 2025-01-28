import asyncio
import os
import logging
import httpx
import json
import random
from datetime import datetime
from typing import List, Dict, Optional
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext,
)
from telegram.error import TelegramError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Updated Constants
BASE_DIR = 'PyGuessgame'
PYDATA_DIR = os.path.join(BASE_DIR, 'Pydata')
QUIZJOIN_PATH = os.path.join(PYDATA_DIR, 'guessjoin.txt')
PUZZLE_PATH = os.path.join(PYDATA_DIR, 'tokenimage.json')
IMAGES_DIR = os.path.join(PYDATA_DIR, 'tokenimage')

# Other existing constants remain the same
AUTHORIZED_ADMINS = ["chicago311", "LesterRonquillo", "Aldrin1212"]
POINTS_PER_CORRECT_ANSWER = 5
HINT_PENALTY = 1
MAX_HINTS = 4  # Maximum number of hints allowed per puzzle

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'guessbot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Disable noisy logs
for logger_name in ["httpx", "telegram.ext._network"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

class QuizGame:
    def __init__(self):
        self.game_active: bool = False
        self.current_puzzle: Optional[Dict] = None
        self.puzzle_data: List[Dict] = []
        self.hints_given: int = 0
        self.setup_files()

    def setup_files(self) -> None:
        """Initialize necessary files and directories."""
        os.makedirs(BASE_DIR, exist_ok=True)
        os.makedirs(PYDATA_DIR, exist_ok=True)
        
        if not os.path.exists(QUIZJOIN_PATH):
            with open(QUIZJOIN_PATH, 'w') as file:
                json.dump([], file, indent=4)
            logger.info(f"Created {QUIZJOIN_PATH}")

        for required_path in [PUZZLE_PATH, IMAGES_DIR]:
            if not os.path.exists(required_path):
                raise FileNotFoundError(f"Required path not found: {required_path}")

        self.puzzle_data = self.load_puzzle()

    @staticmethod
    def load_participate() -> List[Dict]:
        """Load participants data from file."""
        try:
            with open(QUIZJOIN_PATH, 'r') as file:
                participants = json.load(file)
                # Ensure all participants have required fields
                for p in participants:
                    if 'username' not in p:
                        continue
                    p.setdefault('score', 0)
                    p.setdefault('full_name', p.get('username', 'Unknown'))
                    p.setdefault('join_date', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                return participants
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading participants: {e}")
            return []


    @staticmethod
    def save_participate(users: List[Dict]) -> None:
        """Save participants data to file."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(QUIZJOIN_PATH), exist_ok=True)
            
            # Ensure all required fields are present before saving
            for user in users:
                if 'username' not in user:
                    continue
                user['score'] = int(user.get('score', 0))  # Ensure score is an integer
                user.setdefault('full_name', user.get('username', 'Unknown'))
                user.setdefault('join_date', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            # Write to a temporary file first
            temp_path = f"{QUIZJOIN_PATH}.tmp"
            with open(temp_path, 'w') as file:
                json.dump(users, file, indent=4)
            
            # Replace the original file with the temporary file
            os.replace(temp_path, QUIZJOIN_PATH)
            
            logger.info("Participants saved successfully")
        except Exception as e:
            logger.error(f"Error saving participants: {e}")
            raise

    def load_puzzle(self) -> List[Dict]:
        """Load puzzle data from file."""
        try:
            with open(PUZZLE_PATH, 'r') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading puzzles: {e}")
            return []

    def get_hint(self) -> str:
        """Generate a hint for the current puzzle."""
        if not self.current_puzzle:
            return "No active puzzle!"

        answer = os.path.splitext(self.current_puzzle['image'])[0]
        if self.hints_given == 0:
            # First hint: Show length and first letter
            hint = f"Length: {len(answer)} letters\nFirst letter: {answer[0]}"
        elif self.hints_given == 1:
            # Second hint: Show vowels
            hint = ''.join('_' if c not in 'aeiou' else c for c in answer)
        else:
            # Final hint: Show every other letter
            hint = ''.join(c if i % 2 == 0 else '_' for i, c in enumerate(answer))
        
        self.hints_given += 1
        return hint

class QuizBot:
    def __init__(self, token: str):
        self.token = token
        self.quiz_game = QuizGame()
        self.next_game_task = None  # Track the scheduled next game task

    async def start(self, update: Update, context: CallbackContext) -> None:
        """Handle the /startpalaro command."""
        welcome_message = (
            "🎮 Welcome to the Quiz Game! 🎮\n\n"
            "Available commands:\n"
            "/join_participate - Join the game\n"
            "/gamerules - View game rules\n"
            "/scores - View current scores\n"
            "/hint - Get a hint (with point penalty)\n\n"
            "Admin commands:\n"
            "/start_game - Start a new game\n"
            "/end_game - End the current game\n"
            "/next_game - Move to next question\n"
            "/reset_scores - Reset all scores"
        )
        await update.message.reply_text(welcome_message)

    async def rules(self, update: Update, context: CallbackContext) -> None:
        """Handle the /gamerules command."""
        rules_text = (
            "📜 Game Rules 📜\n\n"
            "1. Each correct answer gives you 5 point\n"
            "2. Using limited hints reduces potential points by 1 limited\n"
            "3. You must join using /join_participate to play\n"
            "4. Only registered participants can answer\n"
            "5. First correct answer wins the points"
        )
        await update.message.reply_text(rules_text)

    #------------------------------------------------------------------------------------

    async def join_participate(self, update: Update, context: CallbackContext) -> None:
        """Handle the /join_participate command with beautiful but simple formatting."""
        user = update.message.from_user
        participants = self.quiz_game.load_participate()
    
    # Check if user is already participating
        if any(p['username'] == user.username for p in participants):
            already_joined = (
                f"@{user.username}, you're in the game!\n\n"
                "• /scores - View rankings\n"
                "• /gamerules - Game rules\n"
                "• /hint - Get help\n\n"
                "🎮 Good luck! 🎮"
            )
            await update.message.reply_text(already_joined)
            return

    # Add new participant
        new_participant = {
            "username": user.username,
            "full_name": user.full_name or user.username,
            "score": 0,
            "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        participants.append(new_participant)
        self.quiz_game.save_participate(participants)
    
        welcome_message = (
            f"@{user.username}, ready to play?\n\n"
            "📌 How to Play:\n"
            "• Guess images correctly\n"
            "• Score points\n"
            "• Reach the top!\n\n"
            "Type /scores to check rankings\n"
            "Use /gamerules how to play\n\n"
            "🎯 Good luck! 🎯"
        )

    # Simple inline keyboard
        keyboard = [
            [
              #  InlineKeyboardButton("📜 Rules", callback_data="/gamerules"),
              #  InlineKeyboardButton("🏆 Rankings", callback_data="/scores")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup
        )

    # Simple notification of new player
        notification = f"🎯 @{user.username} joined the game! Total players: {len(participants)}"
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=notification
    )

    #-------------------------------------------------------------------------------

    async def scores(self, update: Update, context: CallbackContext) -> None:
        """Handle the /scores command with beautiful formatting."""
        participants = self.quiz_game.load_participate()
        if not participants:
            await update.message.reply_text("No participants yet! 🎮\nJoin with /join_participate")
            return

        # Sort participants by score and get top 10
        sorted_participants = sorted(participants, key=lambda x: x.get('score', 0), reverse=True)
        top_10 = sorted_participants[:10]

        # Calculate statistics
        total_players = len(participants)
        active_players = sum(1 for p in participants if p.get('score', 0) > 0)
        highest_score = top_10[0].get('score', 0) if top_10 else 0

        # Position suffixes
        suffixes = {
            1: "ˢᵗ", 2: "ⁿᵈ", 3: "ʳᵈ"
        }

        # Create leaderboard text
        leaderboard = "🏆 LEADERBOARD 🏆\n"
        leaderboard += "━━━━━━━━━━━━━━━━━━\n"

        for i, p in enumerate(top_10, 1):
            username = p.get('username', 'Unknown')
            score = p.get('score', 0)

            # Determine position formatting
            if i <= 3:
                medal = ["🥇", "🥈", "🥉"][i-1]
                position = f"{medal} {i}{suffixes.get(i, 'ᵗʰ')}"
            else:
                position = f"🎯 {i}ᵗʰ"

            # Format each line with proper spacing
            leaderboard += f"{position} │ @{username} │ {score} pts\n"

        leaderboard += "\n━━━━━━━━━━━━━━━━━━\n"

        # Add statistics
        leaderboard += "📊 Statistics:\n"
        leaderboard += f"- Total Players: {total_players}\n"
        leaderboard += f"- Active Players: {active_players}\n"
        leaderboard += f"- Highest Score: {highest_score} pts\n\n"

        # Add call to action
        leaderboard += "💡 Join with /join_participate"

        await update.message.reply_text(leaderboard)

   
   #-------------------------------------------------------------------------------

    

    async def hint(self, update: Update, context: CallbackContext) -> None:
        """Handle the /hint command with a limit on hints."""
        if not self.quiz_game.game_active or not self.quiz_game.current_puzzle:
            await update.message.reply_text("No active game!")
            return

        # Check if maximum hints reached
        if self.quiz_game.hints_given >= MAX_HINTS:
            await update.message.reply_text(
                "⚠️ No more hints available!\n"
                "You've used all hints for this puzzle.\n"
                "If you get it right now, you'll receive 0 points."
            )
            return

        # Calculate remaining points if hint is used
        remaining_points = POINTS_PER_CORRECT_ANSWER - ((self.quiz_game.hints_given + 1) * HINT_PENALTY)
        
        hint = self.quiz_game.get_hint()
        hint_message = (
            f"🤔 Hint {self.quiz_game.hints_given}/{MAX_HINTS}:\n"
            f"{hint}\n\n"
            f"📌 Points if correct: {max(remaining_points, 0):.1f}\n"
            f"❗ Hints remaining: {MAX_HINTS - self.quiz_game.hints_given - 1}"
        )
        
        await update.message.reply_text(hint_message)

    #-------------------------------------------------------------------------------

    async def start_game(self, update: Update, context: CallbackContext) -> None:
        """Handle the /start_game command."""
        if not self._is_authorized_admin(update):
            await update.message.reply_text("⛔ You're not authorized to start the game.")
            return

        self.quiz_game.game_active = True
        random.shuffle(self.quiz_game.puzzle_data)
        self.quiz_game.hints_given = 0
        
        # Send and pin the start message
        start_message = await update.message.reply_text(
            "🎮 Game started!\n\nWaiting for first puzzle...",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Start First Round", callback_data="next_game")
            ]])
        )
        
        # Pin the message
        try:
            await context.bot.pin_chat_message(
                chat_id=update.effective_chat.id,
                message_id=start_message.message_id,
                disable_notification=True
            )
        except TelegramError as e:
            logger.error(f"Failed to pin start game message: {e}")

    #-------------------------------------------------------------------------------


    async def end_game(self, update: Update, context: CallbackContext) -> None:
        """Handle the /end_game command."""
        if not self._is_authorized_admin(update):
            await update.message.reply_text("⛔ You're not authorized to end the game.")
            return

        self.quiz_game.game_active = False
        await update.message.reply_text("🏁 Game ended!")

        # Show final scores
        await self.scores(update, context)

    #-------------------------------------------------------------------------------

    async def reset_list(self, update: Update, context: CallbackContext) -> None:
        """Handle the /reset_list command with verification."""
        if not self._is_authorized_admin(update):
            await update.message.reply_text("⛔ You're not authorized to reset scores.")
            return

        # Create verification keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Reset All", callback_data="confirm_reset"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send verification message
        await update.message.reply_text(
            "╔═════════════════════╗\n"
            "║    ⚠️ CONFIRM RESET    ║\n"
            "╚═════════════════════╝\n\n"
            "Are you sure you want to reset all participant data?\n\n"
            "⚠️ This will:\n"
            "• Delete all participant scores\n"
            "• Remove all participants\n"
            "• Require players to /join_participate again\n\n"
            "This action cannot be undone!",
            reply_markup=reply_markup
        )

    async def handle_reset_callback(self, update: Update, context: CallbackContext) -> None:
        """Handle reset confirmation callback."""
        query = update.callback_query
        await query.answer()  # Acknowledge the button click

        if not self._is_authorized_admin(update):
            await query.edit_message_text("⛔ You're not authorized for this action.")
            return

        if query.data == "confirm_reset":
            try:
                # Directly write an empty participants list to the file
                empty_data = []
                with open(QUIZJOIN_PATH, 'w') as file:
                    json.dump(empty_data, file, indent=4)
                
                # Update the message to show success
                await query.edit_message_text(
                    "╔═══════════════════╗\n"
                    "║    ✅ RESET COMPLETE    ║\n"
                    "╚═══════════════════╝\n\n"
                    "All participant data has been cleared!\n"
                    "Players will need to /join_participate again.\n\n"
                    "🕒 Reset completed at: " + 
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                
                logger.info(f"Participant data reset by admin: {update.effective_user.username}")
                
            except Exception as e:
                logger.error(f"Error in reset confirmation: {e}")
                await query.edit_message_text("❌ Error occurred while resetting data. Please try again.")
                
        elif query.data == "cancel_reset":
            # Update the message to show cancellation
            await query.edit_message_text(
                "╔═══════════════════╗\n"
                "║    ❌ RESET CANCELLED    ║\n"
                "╚═══════════════════╝\n\n"
                "Reset operation was cancelled.\n"
                "All participant data remains unchanged."
            )
            logger.info(f"Reset cancelled by admin: {update.effective_user.username}")

    #-------------------------------------------------------------------------------


    async def next_game(self, update: Update, context: CallbackContext) -> None:
        """Handle the /next_game command and callback."""
        if not self._is_authorized_admin(update):
            # For callback queries, answer the query first
            if update.callback_query:
                await update.callback_query.answer("⛔ You're not authorized for this action.")
                return
            # For regular messages
            await update.message.reply_text("⛔ You're not authorized for this action.")
            return

        if not self.quiz_game.game_active:
            reply_text = "No active game! Use /start_game first."
            if update.callback_query:
                await update.callback_query.message.reply_text(reply_text)
            else:
                await update.message.reply_text(reply_text)
            return

        if not self.quiz_game.puzzle_data:
            game_over_text = "🏁 No more puzzles available! Game Over! \n press /scores"
            if update.callback_query:
                await update.callback_query.message.reply_text(game_over_text)
                await self.end_game(update, context)
            else:
                await update.message.reply_text(game_over_text)
                await self.end_game(update, context)
            return

        self.quiz_game.current_puzzle = self.quiz_game.puzzle_data.pop()
        self.quiz_game.hints_given = 0
        # Reset the puzzle solved flag
        self.quiz_game.puzzle_solved = False

        image_path = os.path.join(IMAGES_DIR, self.quiz_game.current_puzzle['image'])
        try:
            with open(image_path, 'rb') as img:
                # Send and pin the new puzzle message
                puzzle_message = await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=InputFile(img),
                    caption="🎯 Guess the image!\n\nUse /hint if you need help with panalty. \n Join Now! /join_participate "
                )
                
                # Pin the new puzzle message
                try:
                    await context.bot.pin_chat_message(
                        chat_id=update.effective_chat.id,
                        message_id=puzzle_message.message_id,
                        disable_notification=True
                    )
                except TelegramError as e:
                    logger.error(f"Failed to pin puzzle message: {e}")
                    
        except Exception as e:
            logger.error(f"Error sending image: {e}")
            error_text = "Error loading puzzle. Please try again."
            if update.callback_query:
                await update.callback_query.message.reply_text(error_text)
            else:
                await update.message.reply_text(error_text)

    #------------------------------------------------------------------------------------

    # Modify the handle_message method to include auto-next game logic
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        if not self.quiz_game.game_active or not self.quiz_game.current_puzzle:
            return

        # Add a flag to track if the puzzle has already been solved
        if hasattr(self.quiz_game, 'puzzle_solved') and self.quiz_game.puzzle_solved:
            return

        username = update.message.from_user.username
        participants = self.quiz_game.load_participate()
        
        if not any(p['username'] == username for p in participants):
            return

        answer = update.message.text.strip().lower()
        expected_answer = os.path.splitext(self.quiz_game.current_puzzle['image'])[0].lower()

        if answer == expected_answer:
            # Mark the puzzle as solved to prevent further point awarding
            self.quiz_game.puzzle_solved = True

            points = POINTS_PER_CORRECT_ANSWER - (self.quiz_game.hints_given * HINT_PENALTY)
            points = max(points, 0)  # Ensure points don't go negative
                
            # Update user's score
            for p in participants:
                if p['username'] == username:
                    p['score'] = p.get('score', 0) + points
                    break
            
            self.quiz_game.save_participate(participants)
            
            # Get user's current rank
            sorted_participants = sorted(participants, key=lambda x: x.get('score', 0), reverse=True)
            user_rank = next(i + 1 for i, p in enumerate(sorted_participants) if p['username'] == username)
            
            # Create congratulations message
            congrats_message = (
                "╔══════════════════════╗\n"
                "║           🥇 FIRST CORRECT! 🥇           ║\n"
                "╚══════════════════════╝\n\n"
                f"🏆 @{username} wins this round!\n"
                f"Answer: {expected_answer}\n\n"
            )

            # Add hint usage information
            if self.quiz_game.hints_given > 0:
                if points > 0:
                    congrats_message += (
                        f"📍 Hints used: {self.quiz_game.hints_given}/{MAX_HINTS}\n"
                        f"🏆 Points Earned: +{points:.1f}\n"
                    )
                else:
                    congrats_message += (
                        "❌ No points awarded - all hints used\n"
                        f"📍 Hints used: {self.quiz_game.hints_given}/{MAX_HINTS}\n"
                    )
            else:
                congrats_message += f"🏆 Perfect Score! +{points:.1f} points\n"

            congrats_message += (
                "━━━━━━━━━━━━━━━━━━\n"
                "📊 Stats Update:\n"
                f"• Rank: #{user_rank}\n"
                f"• Total Score: {p['score']}\n"
            )

            # Add special effects
            if points == POINTS_PER_CORRECT_ANSWER:
                congrats_message += "\n🌟 Perfect Score! No hints used!"
            elif user_rank == 1:
                congrats_message += "\n👑 You're in first place!"

            # Add countdown message for next game
            congrats_message += "\n\n⏳ Next game starts in 60 seconds..."

            # Send main congratulation message
            await update.message.reply_text(congrats_message)

            # Send celebratory sticker
            try:
                stickers = [
                    "CAACAgIAAxkBAAIDHmXFdQ7wmm-sFu6JuqIux3sIcsVzAAJBAQACqCK2G3x_4IZbJSQEMAQ",
                    "CAACAgIAAxkBAAIDH2XFdRXMJ_9bHwXpXNxvzyNLAAHUSQACQwEAAqgithtuHEr3ugABrN4wBA",
                    "CAACAgIAAxkBAAIDIGXFdRmBnFbB6QxQSuvs9Zv2Y4LSAAJFAQACqCK2GzVR4fZ-giwWMAQ"
                ]
                await context.bot.send_sticker(
                    chat_id=update.effective_chat.id,
                    sticker=random.choice(stickers)
                )
            except Exception as e:
                logger.error(f"Error sending sticker: {e}")

            # Schedule next game in 60 seconds
            await self.schedule_next_game(update, context)

    #----------------------------------------------------------------#

    async def schedule_next_game(self, update: Update, context: CallbackContext) -> None:
        # Cancel any existing scheduled next game task
        if self.next_game_task:
            self.next_game_task.cancel()

        # Create a new task to start the next game
        async def delayed_next_game():
            # Wait 60 seconds
            await asyncio.sleep(60)
            
            # Check if game is still active
            if self.quiz_game.game_active:
                # Simulate an admin call to next_game
                await self.next_game(update, context)

        # Schedule the task
        self.next_game_task = asyncio.create_task(delayed_next_game())

    #------------------------------------------------------------------------------------


    async def user_stats(self, update: Update, context: CallbackContext) -> None:
        """Handle the user stats button callback."""
        query = update.callback_query
        await query.answer()
    
        username = query.from_user.username
        participants = self.quiz_game.load_participate()
    
        user_data = next((p for p in participants if p['username'] == username), None)
        if not user_data:
            await query.message.reply_text("User data not found!")
            return

        # Calculate user stats
        sorted_participants = sorted(participants, key=lambda x: x.get('score', 0), reverse=True)
        rank = next(i + 1 for i, p in enumerate(sorted_participants) if p['username'] == username)
        total_participants = len(participants)
    
        stats_message = (
            "╔═══════════════════╗\n"
            "║    📊 YOUR STATS    ║\n"
            "╚═══════════════════╝\n\n"
            f"👤 @{username}\n"
            f"🏆 Rank: #{rank} of {total_participants}\n"
            f"📈 Score: {user_data.get('score', 0)} points\n"
            f"📅 Joined: {user_data.get('join_date', 'Unknown')}\n\n"
            "Keep playing to improve your rank! 🎯"
        )
    
        await query.message.edit_text(
            stats_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="back_to_congrats")
            ]])
        )

    # Update button_callback to handle new buttons
    async def button_callback(self, update: Update, context: CallbackContext) -> None:
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()

        if query.data == "confirm_reset" or query.data == "cancel_reset":
            await self.handle_reset_callback(update, context)
        elif query.data == "rules":
            await self.rules(update, context)
        elif query.data == "scores":
            await self.scores(update, context)
        elif query.data == "howtoplay":
            await self.howtoplay(update, context)
        elif query.data == "user_stats":
            await self.user_stats(update, context)
        elif query.data == "next_game":
            await self.next_game(update, context)

    @staticmethod
    def _is_authorized_admin(update: Update) -> bool:
        """Check if user is an authorized admin."""
        try:
            # Handle both regular messages and callback queries
            user = update.effective_user
            return user.username in AUTHORIZED_ADMINS
        except AttributeError:
            return False

    def run(self):
        """Start the bot."""
        application = Application.builder().token(self.token).build()

     # Add handlers
        application.add_handler(CommandHandler("startpalaro", self.start))
        application.add_handler(CommandHandler("rulesgame", self.rules))
        application.add_handler(CommandHandler("join_participate", self.join_participate))
        application.add_handler(CommandHandler("leaderboard", self.scores))
        application.add_handler(CommandHandler("hint", self.hint))
        application.add_handler(CommandHandler("start_game", self.start_game))
        application.add_handler(CommandHandler("next_game", self.next_game))
        application.add_handler(CommandHandler("reset_scores", self.reset_list))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(CallbackQueryHandler(self.button_callback))

        # Run the application with asyncio support
        import asyncio
        asyncio.run(application.run_polling())

if __name__ == '__main__':
    # Retrieve token from environment variable
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Add a check to ensure token is set
    if not TOKEN:
        logging.error("No Telegram Bot Token found. Please set TELEGRAM_BOT_TOKEN in .env file.")
        exit(1)
    
    quiz_bot = QuizBot(TOKEN)
    quiz_bot.run()