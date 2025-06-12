import os
import logging
from urllib.parse import urljoin, quote_plus
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable or fallback default
BOT_TOKEN = os.getenv("BOT_TOKEN", "8126125634:AAGaEy-7KIxEqucrlrY9VLJwXQ83dm7hQaU")

if not BOT_TOKEN:
    logger.error("Bot token not found. Please set the BOT_TOKEN environment variable.")
    exit(1)

# Headers to mimic a real browser request
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

async def scrape_ocean_pdf(query: str) -> dict:
    try:
        encoded_query = quote_plus(query)
        search_url = f"https://oceanofpdf.com/?s={encoded_query}"
        logger.info(f"Scraping Ocean of PDF with URL: {search_url}")
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        book_links = []
        selectors = [
            'article h2 a',
            '.post-title a',
            'h2.entry-title a',
            '.entry-header h2 a',
            'article .entry-title a',
            '.post h2 a',
        ]
        for selector in selectors:
            links = soup.select(selector)
            if links:
                book_links = links
                break

        if not book_links:
            articles = soup.find_all('article')
            for article in articles:
                links = article.find_all('a', href=True)
                for link in links:
                    if link.get('href') and link.get_text(strip=True):
                        book_links.append(link)
                        break
                if book_links:
                    break

        if not book_links:
            return {
                'success': False,
                'error': 'No search results found',
                'message': f"No books found for '{query}'. Try a different search term."
            }

        first_book = book_links[0]
        book_title = first_book.get_text(strip=True)
        book_url = first_book.get('href')

        if book_url.startswith('/'):
            book_url = urljoin('https://oceanofpdf.com', book_url)
        elif not book_url.startswith('http'):
            book_url = f"https://oceanofpdf.com/{book_url}"

        return {
            'success': True,
            'title': book_title,
            'url': book_url,
            'search_url': search_url
        }

    except requests.exceptions.Timeout:
        logger.error(f"Timeout while scraping Ocean of PDF for query: {query}")
        return {
            'success': False,
            'error': 'Request timeout',
            'message': "The search took too long. Please try again."
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while scraping Ocean of PDF: {e}")
        return {
            'success': False,
            'error': 'Network error',
            'message': "Unable to connect to Ocean of PDF. Please try again later."
        }
    except Exception as e:
        logger.error(f"Unexpected error while scraping Ocean of PDF: {e}")
        return {
            'success': False,
            'error': 'Parsing error',
            'message': "Unable to parse search results. The website structure may have changed."
        }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        welcome_message = (
            "👋 Welcome to My Books. Here you can get any book you want as PDF 📚📚📚📚📚\n"
            "Just type the *book name* and I will do the rest."
        )
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        logger.info(f"Start command handled for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text("❌ Sorry, something went wrong. Please try again.")

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        help_message = (
            "📘 *Ocean of PDF Search Bot Help*\n\n"
            "👋 *Available Commands:*\n"
            "• /start - Welcome message and instructions\n"
            "• /help - Show this help message\n\n"
            "📚 *How to search:*\n"
            "Just send me any book title and I'll generate a search link!\n\n"
            "🔍 *Examples:*\n"
            "• The Alchemist\n"
            "• Python Crash Course\n"
            "• To Kill a Mockingbird\n\n"
            "🌐 I'll create a direct link to search Ocean of PDF for your book!"
        )
        await update.message.reply_text(help_message, parse_mode='Markdown')
        logger.info(f"Help command handled for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in help handler: {e}")
        await update.message.reply_text("❌ Sorry, something went wrong. Please try again.")

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.message.text.strip()
        if not query:
            await update.message.reply_text(
                "📖 Please send me a book name to search for!\n"
                "Example: 'The Great Gatsby' or 'Python Programming'"
            )
            return

        if len(query) < 2:
            await update.message.reply_text("🔍 Please provide a longer book title (at least 2 characters).")
            return

        encoded_query = quote_plus(query)
        search_url = f"https://oceanofpdf.com/?s={encoded_query}"

        response_message = (
            f"🔎 Here's your book download link:\n\n"
            f"📚 *Book:* {query}\n"
            f"🌐 *Link:* {search_url}\n\n"
            f"💡 Click the link above to download '{query}' in PDF!"
        )

        await update.message.reply_text(response_message, parse_mode='Markdown')
        logger.info(f"Search handled for user {update.effective_user.id}, query: {query}")

    except Exception as e:
        logger.error(f"Error in search handler: {e}")
        await update.message.reply_text(
            "❌ Sorry, I couldn't process your search request. Please try again.\n"
            "Make sure you're sending a valid book title."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))
        app.add_error_handler(error_handler)

        logger.info("Ocean of PDF search bot started successfully! Polling for messages...")
        print("🤖 Bot is running! Send book titles to get Ocean of PDF search links.")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ Failed to start bot: {e}")
        print("Please check your BOT_TOKEN environment variable.")

if __name__ == "__main__":
    main()
