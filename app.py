#!/usr/bin/env python3
"""
Web dashboard for the Office Memes Telegram Bot
Provides analytics, meme management, and configuration interface.
"""
import os
import json
import logging
import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv

# Import meme-related modules
from meme_data import MEMES
import meme_analytics
import recommendation_engine
from recommendation_engine import load_preferences, get_user_preferences_stats

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "office_memes_dashboard_secret")

# Constants
ANALYTICS_DIR = "analytics"
MEMES_CACHE_FILE = "cached_filtered_memes.json"
REJECTED_CACHE_FILE = "rejected_memes.json"

# Load cached memes
def load_memes():
    """Load memes from cache or use default collection"""
    try:
        if os.path.exists(MEMES_CACHE_FILE):
            with open(MEMES_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return MEMES
    except Exception as e:
        logger.error(f"Error loading memes: {e}")
        return MEMES

# Load rejected memes
def load_rejected_memes():
    """Load rejected memes from cache file"""
    try:
        if os.path.exists(REJECTED_CACHE_FILE):
            with open(REJECTED_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading rejected memes: {e}")
        return {}

# Load user preferences for recommendations
def load_user_data():
    """Load user preference data for recommendation analysis"""
    try:
        load_preferences()
        # Создаем общую статистику вместо вызова get_user_preferences_stats без user_id
        total_users = len(recommendation_engine.user_preferences)
        active_users = sum(1 for prefs in recommendation_engine.user_preferences.values() 
                          if prefs.get("rated_memes", []))
        
        # Средняя оценка на пользователя
        rated_counts = [len(prefs.get("rated_memes", [])) 
                       for prefs in recommendation_engine.user_preferences.values()]
        average_ratings = sum(rated_counts) / total_users if total_users > 0 else 0
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "average_ratings": round(average_ratings, 1),
            "popular_keywords": {}  # Заглушка для popular_keywords
        }
    except Exception as e:
        logger.error(f"Error loading user preferences: {e}")
        return {"total_users": 0, "active_users": 0, "average_ratings": 0}

# Routes
@app.route('/')
def index():
    """Dashboard home page with summary statistics"""
    # Get analytics data
    memes_count = len(load_memes())
    rejected_count = len(load_rejected_memes())
    
    # Get session stats
    session_stats = {
        "total_sessions": meme_analytics.session_stats.get("total_sessions", 0),
        "active_users": meme_analytics.session_stats.get("active_users", 0),
        "today_ratings": meme_analytics.session_stats.get("today_ratings", 0),
        "total_ratings": meme_analytics.session_stats.get("total_ratings", 0)
    }
    
    # Get user preference stats
    user_stats = load_user_data()
    
    # Добавим текущую дату для шаблона
    now = datetime.datetime.now()
    
    return render_template('index.html', 
                          memes_count=memes_count,
                          rejected_count=rejected_count,
                          session_stats=session_stats,
                          user_stats=user_stats,
                          now=now)

@app.route('/memes')
def memes():
    """Meme collection browser page"""
    memes_collection = load_memes()
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    
    # Convert memes dictionary to list for pagination
    memes_list = [{"id": meme_id, **meme_data} for meme_id, meme_data in memes_collection.items()]
    
    # Simple pagination
    total_pages = (len(memes_list) + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paged_memes = memes_list[start_idx:end_idx]
    
    # Добавим текущую дату для шаблона
    now = datetime.datetime.now()
    
    return render_template('memes.html', 
                          memes=paged_memes,
                          page=page, 
                          per_page=per_page,
                          total_pages=total_pages,
                          total_memes=len(memes_list),
                          now=now)

@app.route('/analytics')
def analytics():
    """Analytics dashboard page"""
    # Get popular memes analytics
    popular_memes = meme_analytics.get_popular_memes(limit=10)
    
    # Get trending memes
    trending_memes = meme_analytics.get_trending_memes(limit=10)
    
    # Get user activity (использовать пустой список, если метод отсутствует)
    user_activity = []
    
    # Get overall statistics
    overall_stats = {
        "total_views": sum(meme.get("views", 0) for meme in meme_analytics.popular_memes.values()),
        "total_likes": sum(meme.get("likes", 0) for meme in meme_analytics.popular_memes.values()),
        "total_dislikes": sum(meme.get("dislikes", 0) for meme in meme_analytics.popular_memes.values()),
    }
    
    # Timeline data for last 7 days (заглушка, если метод отсутствует)
    timeline_data = []
    
    # Добавим текущую дату для шаблона
    now = datetime.datetime.now()
    
    return render_template('analytics.html',
                          popular_memes=popular_memes,
                          trending_memes=trending_memes,
                          user_activity=user_activity,
                          overall_stats=overall_stats,
                          timeline_data=timeline_data,
                          now=now)

@app.route('/users')
def users():
    """User management and analysis page"""
    # Get user preferences and history
    try:
        load_preferences()
        user_data = {}
        
        # Convert user IDs from strings to integers for display
        for user_id_str, prefs in meme_analytics.user_activity.items():
            user_id = int(user_id_str) if user_id_str.isdigit() else user_id_str
            user_data[user_id] = {
                "ratings": prefs.get("ratings", 0),
                "sessions": prefs.get("sessions", 0),
                "last_active": datetime.datetime.fromtimestamp(
                    prefs.get("last_active", 0)
                ).strftime('%Y-%m-%d %H:%M:%S') if prefs.get("last_active", 0) > 0 else "Never"
            }
        
        # Sort users by ratings count (descending)
        sorted_users = sorted(user_data.items(), key=lambda x: x[1]["ratings"], reverse=True)
        
        # Добавим текущую дату для шаблона
        now = datetime.datetime.now()
        
        return render_template('users.html', users=sorted_users, now=now)
    
    except Exception as e:
        logger.error(f"Error loading user data: {e}")
        flash(f"Error loading user data: {e}", "danger")
        # Добавим текущую дату для шаблона даже при ошибке
        now = datetime.datetime.now()
        return render_template('users.html', users=[], now=now)

@app.route('/settings')
def settings():
    """Bot settings and configuration page"""
    # Get current settings
    bot_settings = {
        "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", "Not configured"),
        "VK_TOKEN": os.environ.get("VK_TOKEN", "Not configured"),
        "UPDATE_INTERVAL": 3600,  # 1 hour in seconds
        "MIN_MEMES_COUNT": 50,
        "MAX_MEMES_TO_FETCH": 20
    }
    
    # Make the tokens partially hidden for security
    if bot_settings["TELEGRAM_BOT_TOKEN"] != "Not configured":
        token = bot_settings["TELEGRAM_BOT_TOKEN"]
        bot_settings["TELEGRAM_BOT_TOKEN"] = f"{token[:6]}...{token[-6:]}"
    
    if bot_settings["VK_TOKEN"] != "Not configured":
        token = bot_settings["VK_TOKEN"]
        bot_settings["VK_TOKEN"] = f"{token[:6]}...{token[-6:]}"
    
    # Добавим текущую дату для шаблона
    now = datetime.datetime.now()
    
    return render_template('settings.html', settings=bot_settings, now=now)

# API endpoints for AJAX requests
@app.route('/api/popular_memes')
def api_popular_memes():
    """API endpoint for popular memes data"""
    limit = request.args.get('limit', 10, type=int)
    popular_memes = meme_analytics.get_popular_memes(limit=limit)
    return jsonify(popular_memes)

@app.route('/api/trending_memes')
def api_trending_memes():
    """API endpoint for trending memes data"""
    limit = request.args.get('limit', 10, type=int)
    trending_memes = meme_analytics.get_trending_memes(limit=limit)
    return jsonify(trending_memes)

@app.route('/api/rating_timeline')
def api_rating_timeline():
    """API endpoint for rating timeline data"""
    days = request.args.get('days', 7, type=int)
    # Заглушка, так как метод get_rating_timeline отсутствует
    timeline_data = []
    return jsonify(timeline_data)

@app.route('/api/active_users')
def api_active_users():
    """API endpoint for active users data"""
    limit = request.args.get('limit', 10, type=int)
    # Заглушка, так как метод get_active_users отсутствует
    active_users = []
    return jsonify(active_users)

@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 error page"""
    now = datetime.datetime.now()
    return render_template('base.html', error="Page not found", now=now), 404

@app.errorhandler(500)
def server_error(e):
    """Custom 500 error page"""
    now = datetime.datetime.now()
    return render_template('base.html', error="Internal server error", now=now), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
