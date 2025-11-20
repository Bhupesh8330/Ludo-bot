import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from random import randint
import os

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token - use environment variable in production
BOT_TOKEN = os.getenv('BOT_TOKEN', "7910643925:AAFMhRCzKgj3SfzSwOkvF0sjARuZp7ee0ak")

class LudoGame:
    def __init__(self, max_players=4):
        self.max_players = max_players
        self.players = []  # List of tuples: (user_id, username, emoji)
        self.positions = {}  # user_id -> position
        self.colors = ['🔴', '🔵', '🟢', '🟡', '🟣', '🟠']  # Player colors
        self.current_turn = 0
        self.started = False
        self.game_over = False
        self.winner = None
    
    def add_player(self, user_id: int, username: str) -> tuple:
        """Add player to the game"""
        if self.started:
            return False, "Game has already started!"
        
        if len(self.players) >= self.max_players:
            return False, f"Game is full! Maximum {self.max_players} players allowed."
        
        if any(player[0] == user_id for player in self.players):
            return False, "You have already joined the game!"
        
        # Assign color emoji to player
        color = self.colors[len(self.players)]
        self.players.append((user_id, username, color))
        self.positions[user_id] = 0
        
        return True, f"{color} {username} joined the game! ({len(self.players)}/{self.max_players})"
    
    def start_game(self) -> bool:
        """Start the game if enough players"""
        if len(self.players) >= 2 and not self.started:
            self.started = True
            self.current_turn = 0
            return True
        return False
    
    def roll_dice(self) -> int:
        """Roll a dice (1-6)"""
        return randint(1, 6)
    
    def get_current_player(self) -> tuple:
        """Get current player's info"""
        if not self.players:
            return None
        return self.players[self.current_turn]
    
    def move_player(self, user_id: int, steps: int) -> tuple:
        """Move player and check win condition"""
        if user_id not in self.positions:
            return False, "Player not found"
        
        self.positions[user_id] += steps
        new_position = self.positions[user_id]
        
        # Check win condition
        if new_position >= 50:  # Reduced for faster games
            self.game_over = True
            player_name = next(player[1] for player in self.players if player[0] == user_id)
            self.winner = player_name
            return True, f"🎉 {player_name} WINS! Reached position {new_position}! 🏆"
        
        return False, f"Moved to position {new_position}"
    
    def next_turn(self):
        """Move to next player's turn"""
        self.current_turn = (self.current_turn + 1) % len(self.players)
    
    def get_game_board(self) -> str:
        """Create a visual representation of the game board"""
        if not self.players:
            return "No players in the game."
        
        board = "🎮 **Current Game Board:**\n\n"
        
        for user_id, username, color in self.players:
            position = self.positions.get(user_id, 0)
            turn_indicator = "🎲" if self.players.index((user_id, username, color)) == self.current_turn else "  "
            board += f"{turn_indicator} {color} {username}: Position {position}\n"
        
        if self.game_over and self.winner:
            board += f"\n🏆 **GAME OVER!** 🏆\n{self.winner} wins! 🎉"
        
        return board

# Global game instance
game = LudoGame(max_players=4)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        welcome_text = """
🎲 **Welcome to Ludo Game Bot!** 🎲

**How to play:**
1. Use `/join` to join the game
2. Wait for players (2-4 players needed)
3. Use `/startgame` to begin
4. Use `/roll` when it's your turn
5. First to reach position 50 wins! 🏆

**Commands:**
/join - Join the game
/startgame - Start the game
/roll - Roll the dice
/board - Show game board
/status - Game status
/reset - Reset game

Enjoy! 🎯
        """
        await update.message.reply_text(welcome_text)
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text("❌ Error starting the bot. Please try again.")

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /join command"""
    try:
        user = update.effective_user
        success, message = game.add_player(user.id, user.first_name)
        
        await update.message.reply_text(message)
        
        # If we have enough players, suggest starting
        if success and len(game.players) >= 2:
            await update.message.reply_text(
                f"✅ Enough players to start! Use `/startgame` to begin the game!"
            )
            
    except Exception as e:
        logger.error(f"Error in join_command: {e}")
        await update.message.reply_text("❌ Error joining the game. Please try again.")

async def start_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /startgame command"""
    try:
        if game.started:
            await update.message.reply_text("ℹ️ Game is already running!")
            return
        
        if len(game.players) < 2:
            await update.message.reply_text(
                f"❌ Need at least 2 players to start! Currently {len(game.players)}/{game.max_players} players."
            )
            return
        
        if game.start_game():
            # Animation effect
            messages = [
                "🎮 Starting Ludo Game...",
                "🎮🎲 Shuffling players...",
                "🎮🎲🎯 Game starting...",
                "✅ **Game Started!** 🎉"
            ]
            
            msg = await update.message.reply_text(messages[0])
            for text in messages[1:]:
                await asyncio.sleep(1)
                await msg.edit_text(text)
            
            # Show initial board and first player
            current_player = game.get_current_player()
            if current_player:
                user_id, username, color = current_player
                await update.message.reply_text(
                    f"🎲 First turn: {color} {username}\n"
                    f"Use `/roll` to roll the dice!"
                )
                await show_board(update)
        else:
            await update.message.reply_text("❌ Could not start the game.")
            
    except Exception as e:
        logger.error(f"Error in start_game_command: {e}")
        await update.message.reply_text("❌ Error starting the game. Please try again.")

async def roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /roll command"""
    try:
        user = update.effective_user
        
        if not game.started:
            await update.message.reply_text("❌ Game hasn't started yet! Use `/startgame` to begin.")
            return
        
        if game.game_over:
            await update.message.reply_text(f"🎉 Game over! {game.winner} won! Use `/reset` to play again.")
            return
        
        current_player = game.get_current_player()
        if not current_player:
            await update.message.reply_text("❌ No players in the game!")
            return
        
        current_user_id, current_username, color = current_player
        
        # Check if it's the user's turn
        if user.id != current_user_id:
            await update.message.reply_text(
                f"❌ It's not your turn! Current turn: {color} {current_username}"
            )
            return
        
        # Roll the dice with animation
        rolling_msg = await update.message.reply_text("🎲 Rolling dice...")
        await asyncio.sleep(1)
        
        dice_value = game.roll_dice()
        await rolling_msg.edit_text(f"🎲 {color} {current_username} rolled a **{dice_value}**!")
        
        # Move player
        is_win, move_message = game.move_player(user.id, dice_value)
        
        if is_win:
            await update.message.reply_text(f"🎉 {move_message}")
            game.game_over = True
        else:
            await update.message.reply_text(f"📍 {move_message}")
            
            # Move to next turn
            game.next_turn()
            next_player = game.get_current_player()
            if next_player:
                next_user_id, next_username, next_color = next_player
                await update.message.reply_text(
                    f"➡️ Next turn: {next_color} {next_username}\n"
                    f"Use `/roll` to take your turn!"
                )
        
        # Show updated board
        await show_board(update)
        
    except Exception as e:
        logger.error(f"Error in roll_command: {e}")
        await update.message.reply_text("❌ Error rolling dice. Please try again.")

async def board_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /board command"""
    try:
        await show_board(update)
    except Exception as e:
        logger.error(f"Error in board_command: {e}")
        await update.message.reply_text("❌ Error displaying board.")

async def show_board(update: Update):
    """Show the game board"""
    board_text = game.get_game_board()
    await update.message.reply_text(board_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    try:
        status_text = "📊 **Game Status:**\n\n"
        status_text += f"Players: {len(game.players)}/{game.max_players}\n"
        status_text += f"Game Started: {'✅ Yes' if game.started else '❌ No'}\n"
        status_text += f"Game Over: {'✅ Yes' if game.game_over else '❌ No'}\n"
        
        if game.players:
            status_text += f"\n**Players:**\n"
            for user_id, username, color in game.players:
                position = game.positions.get(user_id, 0)
                status_text += f"{color} {username} - Position {position}\n"
        
        if game.started and not game.game_over:
            current_player = game.get_current_player()
            if current_player:
                user_id, username, color = current_player
                status_text += f"\n🎲 **Current Turn:** {color} {username}"
        
        if game.winner:
            status_text += f"\n🏆 **Winner:** {game.winner}"
        
        await update.message.reply_text(status_text)
        
    except Exception as e:
        logger.error(f"Error in status_command: {e}")
        await update.message.reply_text("❌ Error getting game status.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reset command"""
    try:
        global game
        game = LudoGame(max_players=4)
        await update.message.reply_text("🔄 Game has been reset! Use `/join` to start a new game.")
        
    except Exception as e:
        logger.error(f"Error in reset_command: {e}")
        await update.message.reply_text("❌ Error resetting game.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🆘 **Ludo Game Bot Help**

**Game Rules:**
- 2-4 players can join
- Take turns rolling dice with `/roll`
- First to reach position 50 wins
- Only current player can roll

**Commands:**
/start - Start the bot and see instructions
/join - Join the current game
/startgame - Start the game (need 2+ players)
/roll - Roll the dice (your turn only)
/board - Show current game board
/status - Show game status
/reset - Reset the current game
/help - Show this help message

**Enjoy playing!** 🎲
    """
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any non-command messages"""
    await update.message.reply_text(
        "🤖 I'm a Ludo Game Bot! Use /start to see how to play or /help for commands."
    )

def main():
    """Start the bot"""
    try:
        # Create application
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("join", join_command))
        application.add_handler(CommandHandler("startgame", start_game_command))
        application.add_handler(CommandHandler("roll", roll_command))
        application.add_handler(CommandHandler("board", board_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("reset", reset_command))
        application.add_handler(CommandHandler("help", help_command))
        
        # Handle non-command messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Start the bot
        print("🤖 Ludo Game Bot is running...")
        print("Press Ctrl+C to stop")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        print(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    main()
