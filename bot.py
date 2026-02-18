import logging
import os
from telegram import Update, User
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token depuis les variables d'environnement (sécurisé)
TOKEN = os.environ.get("8262038457:AAFyItKNmtr2l1bNZcfBbCSYebwA7lpcXrM")

# Dictionnaire pour stocker les membres par groupe
membres_groupes = {}


async def enregistrer_membre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enregistre automatiquement chaque membre qui envoie un message"""
    if not update.effective_user or not update.effective_chat:
        return
    
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if user.is_bot:
        return
    
    if chat_id not in membres_groupes:
        membres_groupes[chat_id] = {}
    
    if user.username:
        membres_groupes[chat_id][user.username.lower()] = user
    
    membres_groupes[chat_id][str(user.id)] = user


async def profil_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Commande /profil @nom - Affiche le profil d'un membre"""
    message = update.message
    chat = update.effective_chat
    
    if chat.type not in ['group', 'supergroup']:
        await message.reply_text("❌ Cette commande ne fonctionne que dans les groupes !")
        return
    
    chat_id = chat.id
    target_user = None
    
    # Cas 1: Réponse à un message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
    
    # Cas 2: @username ou ID fourni
    elif context.args:
        recherche = context.args[0].lstrip('@').lower()
        
        if chat_id in membres_groupes and recherche in membres_groupes[chat_id]:
            target_user = membres_groupes[chat_id][recherche]
        
        if not target_user:
            try:
                admins = await context.bot.get_chat_administrators(chat_id)
                for admin in admins:
                    if admin.user.username and admin.user.username.lower() == recherche:
                        target_user = admin.user
                        break
            except Exception as e:
                logger.error(f"Erreur: {e}")
        
        if not target_user:
            await message.reply_text(
                f"❌ Membre @{recherche} non trouvé.\n"
                f"💡 La personne doit d'abord envoyer un message dans ce groupe !",
                parse_mode='Markdown'
            )
            return
    else:
        await message.reply_text(
            "📖 **Utilisation:**\n"
            "`/profil @nom` - Voir un profil\n"
            "`/profil` (en réponse) - Profil de l'auteur",
            parse_mode='Markdown'
        )
        return
    
    if target_user:
        profil_text = generer_profil(target_user)
        try:
            photos = await context.bot.get_user_profile_photos(target_user.id, limit=1)
            if photos and photos.photos:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photos.photos[0][-1].file_id,
                    caption=profil_text,
                    parse_mode='Markdown',
                    reply_to_message_id=message.message_id
                )
            else:
                await message.reply_text(profil_text, parse_mode='Markdown')
        except:
            await message.reply_text(profil_text, parse_mode='Markdown')


def generer_profil(user: User) -> str:
    """Génère le texte du profil"""
    nom = user.full_name or "Sans nom"
    username = f"@{user.username}" if user.username else "Aucun"
    user_id = user.id
    langue = user.language_code.upper() if user.language_code else "?"
    statut = "🤖 Bot" if user.is_bot else "👤 Humain"
    premium = "💎 Premium" if user.is_premium else "⭐ Standard"
    
    return f"""
👤 **PROFIL**

📝 **Nom:** `{nom}`
🔖 **Username:** {username}
🆔 **ID:** `{user_id}`
🌐 **Langue:** {langue}
{statut} | {premium}
"""


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Commande /start"""
    await update.message.reply_text(
        "👋 **Bot de Profil**\n\n"
        "Je mémorise les membres qui parlent et affiche leurs infos.\n\n"
        "📋 `/profil @nom` - Voir un profil\n"
        "💡 Réponds `/profil` à un message pour voir son auteur"
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestion des erreurs"""
    logger.error(f"Erreur: {context.error}")


def main() -> None:
    """Démarrage du bot"""
    if not TOKEN:
        logger.error("BOT_TOKEN non défini !")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # Enregistrer les membres
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, enregistrer_membre))
    
    # Commandes
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("profil", profil_command))
    
    # Erreurs
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Bot démarré sur Render !")
    
    # Démarrer le bot (webhook pour Render)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()