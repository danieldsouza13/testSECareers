import discord
import asyncio
from discord.ext import commands, tasks
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup

# Load env variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True  # Add this line
bot = commands.Bot(command_prefix='!', intents=intents)

from pymongo import MongoClient
from datetime import datetime

class OpportunityDatabase:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['internships_db']
        self.opportunities = self.db['opportunities']
        
        self.opportunities.create_index([
            ("company", 1),
            ("title", 1),
            ("location", 1),
            ("date_posted", 1),
        ], unique=True)
    
    def add_opportunity(self, opp):
        try:
            opp['timestamp'] = datetime.now()
            result = self.opportunities.insert_one(opp)
            return True
        except Exception as e:
            print(f"Error adding opportunity: {e}")
            return False
    
    def get_latest_opportunities(self, limit=5):
        return list(self.opportunities.find(
            {}, 
            {'_id': 0}
        ).sort('timestamp', -1).limit(limit))
    
    def opportunity_exists(self, opp):
        return self.opportunities.find_one({
            'company': opp['company'],
            'title': opp['title'],
            'location': opp['location']
        }) is not None

def fetch_github_opportunities(repo_url, test_date=None):
    try:
        response = requests.get(repo_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        main_repo = "https://github.com/SimplifyJobs/Summer2025-Internships"
        offseason_repo = "https://github.com/SimplifyJobs/Summer2025-Internships/blob/dev/README-Off-Season.md"
        newgrad_repo = "https://github.com/SimplifyJobs/New-Grad-Positions"
        
        opportunities = []
        tables = soup.find_all('table')
        current_company = ""
        
        if test_date:
            target_date = datetime.strptime(test_date, "%B %d, %Y").strftime("%b %d")
        else:
            target_date = datetime.now().strftime("%b %d")
            
        print(f"Searching for opportunities posted on: {target_date}")
        
        for table in tables:
            rows = table.find_all('tr')[1:]
            for row in rows:
                cols = row.find_all('td')
                
                # valid table
                if len(cols) >= 5:

                    if repo_url == offseason_repo:
                        date_posted = cols[-1].text.strip()
                        company_text = cols[0].text.strip()
                        title = cols[1].text.strip()
                        location = cols[2].text.strip()
                        terms = cols[3].text.strip()
                        link = cols[4].find('a')['href'] if cols[4].find('a') else None
                        if link == None:
                            continue
                    
                    elif repo_url == main_repo:
                        date_posted = cols[4].text.strip()
                        company_text = cols[0].text.strip()
                        title = cols[1].text.strip()
                        location = cols[2].text.strip()
                        terms = "Summer 2025"
                        link = cols[3].find('a')['href'] if cols[3].find('a') else None
                        if link == None:
                            continue
                    
                    elif repo_url == newgrad_repo:
                        date_posted = cols[4].text.strip()
                        company_text = cols[0].text.strip()
                        title = cols[1].text.strip()
                        location = cols[2].text.strip()
                        terms = "New Grad"
                        link = cols[3].find('a')['href'] if cols[3].find('a') else None
                        if link == None:
                            continue
                    
                    # Handle company name for arrow cases
                    if company_text == "↳":
                        company = current_company
                    else:
                        company = company_text
                        current_company = company
                    
                    if date_posted == target_date:
                        # Convert date to full format for storage
                        full_date = datetime.strptime(date_posted + " 2024", "%b %d %Y").strftime("%B %d, %Y")

                        location_cell = cols[2]
                        locations = []
                        for text in location_cell.stripped_strings:
                            # Skip the "▼ locations" text
                            if not text.endswith('locations') and '▼' not in text:
                                locations.append(text.strip())
                        formatted_locations = '; '.join(locations)

                        opportunity = {
                            "company": company, 
                            "title": title,
                            "location": formatted_locations,
                            "link": link,
                            "date_posted": full_date,
                            "terms": terms,
                            "sponsorship": determine_sponsorship(title)  
                        }
                        opportunities.append(opportunity)

        return opportunities
    except Exception as e:
        print(f"Error fetching GitHub opportunities: {e}")
        return []


def fetch_linkedin_opportunities():
    """Fetch internships from LinkedIn using web scraping"""
    try:
        url = "https://www.linkedin.com/jobs/search/?keywords=software%20engineering%20intern&location=United%20States"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        opportunities = []
        job_cards = soup.find_all('div', class_='base-card')
        
        for card in job_cards:
            title = card.find('h3', class_='base-search-card__title').text.strip()
            company = card.find('h4', class_='base-search-card__subtitle').text.strip()
            location = card.find('span', class_='job-search-card__location').text.strip()
            link = card.find('a', class_='base-card__full-link')['href']
            
            opportunity = {
                "title": title,
                "company": company,
                "location": location,
                "link": link
            }
            opportunities.append(opportunity)
        
        return opportunities
    except Exception as e:
        print(f"Error fetching LinkedIn opportunities: {e}")
        return []


def fetch_opportunities(test_date=None):
    db = OpportunityDatabase()
    opportunities = []
    
    main_repo = "https://github.com/SimplifyJobs/Summer2025-Internships"
    offseason_repo = "https://github.com/SimplifyJobs/Summer2025-Internships/blob/dev/README-Off-Season.md"
    newgrad_repo = "https://github.com/SimplifyJobs/New-Grad-Positions"

    new_opportunities = (
        fetch_github_opportunities(main_repo, test_date) + 
        fetch_github_opportunities(offseason_repo, test_date) +
        fetch_github_opportunities(newgrad_repo, test_date)
    )
    
    # Only add new opportunities to database
    for opp in new_opportunities:
        if not db.opportunity_exists(opp):
            db.add_opportunity(opp)
            opportunities.append(opp)
    
    return opportunities
   
    '''
    # Mock data
    return [
        {
            "title": "Software Engineering Intern",
            "company": "TechCorp",
            "location": "Remote",
            "description": "Join our team for a summer internship!",
            "deadline": "2025-03-01",
            "link": "https://example.com/job1"
        },
        {
            "title": "Data Science Intern",
            "company": "DataInc",
            "location": "New York, NY",
            "description": "Apply your ML skills in a real-world setting.",
            "deadline": "2025-02-15",
            "link": "https://example.com/job2"
        }
    ]
    '''

def create_opportunity_embed(opp):
    """Create a Discord message embedding for an opportunity"""
    embed = discord.Embed(color=discord.Color.blue())
    
    # Company name
    embed.description = f"### **{opp['company']}**\n\n"

    # Company logo
    company_name = opp['company'].lower().replace(' ', '')
    logo_url = f"https://logo.clearbit.com/{company_name}.com"
    embed.set_thumbnail(url=logo_url)

    # Position title 
    embed.description += f"### [**{opp['title']}**]({opp.get('link', '')})\n\n" 
    
    # Locations
    embed.add_field(name="📍 Location(s)", value=opp['location'], inline=False)
    
    # Terms
    embed.add_field(name="🗓 Term(s)", value=opp['terms'], inline=False)
    
    # Sponsorship
    embed.add_field(name="🌐 Sponsorship", value=opp['sponsorship'], inline=False)

    # Applicant Year
    
    return embed

@tasks.loop(hours=24)
async def post_opportunities(test_date=None):
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            print(f"Error: Could not find channel with ID {CHANNEL_ID}")
            return

        today = datetime.strptime(test_date, "%B %d, %Y") if test_date else datetime.now()
        thread_name = f"📆 {today.strftime('%B %d, %Y')}"

        opportunities = fetch_opportunities(test_date)
        if not opportunities:
            print(f"No new opportunities posted on {today.strftime('%B %d, %Y')}")
            return
        
        daily_thread = await channel.create_thread(
            name=thread_name,
            content=f"{len(opportunities)} new opportunities posted on FALL '24: {today.strftime('%B %d, %Y')}",
            auto_archive_duration=1440
        )

        role_categories = {
            'General SWE': '💻',
            'Frontend': '</>',
            'Backend': '⚙️',
            'Full Stack': '🔄',
            'Mobile': '📱',
            'DevOps/Cloud': '♾️',
            'AI/ML': '🤖',
            'Data Science': '📊',
            'Embedded': '🔌',
            'Security': '🔒',
            'Research': '🔬',
            'Product/TPM': '📋',
            'Other': '🔗'
        }

        # Sort opportunities into categories
        categorized_opps = {category: [] for category in role_categories.keys()}
        for opp in opportunities:
            category = determine_role_category(opp)
            # Remove emoji from category name for sorting
            clean_category = ''.join(c for c in category if not ord(c) > 127)
            clean_category = clean_category.strip()
            if clean_category in categorized_opps:
                categorized_opps[clean_category].append(opp)

        # Post opportunities by category with dividers
        first_category = True
        for category, opps in categorized_opps.items():
            if opps:
                if not first_category:
                    await daily_thread.thread.send('────────────────────────────────')
                
                # Post category header with emoji
                await daily_thread.thread.send(f"{role_categories[category]} {category}")
                
                # Post opportunities in category
                for opp in opps:
                    embed = create_opportunity_embed(opp)
                    await daily_thread.thread.send(embed=embed)
                    await asyncio.sleep(1)
                
                first_category = False

    except Exception as e:
        print(f"Error in post_opportunities: {str(e)}")

def determine_role_category(opp):
    """Determine the role category based on job title and description"""
    title = opp['title'].lower()
    keywords = {
        'General SWE': ['software engineer', 'swe', 'software developer'],
        'Frontend': ['frontend', 'ui', 'react', 'angular', 'javascript'],
        'Backend': ['backend', 'api', 'server', 'java', 'python', 'golang', 'database'],
        'Full Stack': ['full stack', 'fullstack', 'full-stack', 'web development'],
        'Mobile': ['mobile', 'ios', 'android', 'flutter', 'react native'],
        'DevOps/Cloud': ['devops', 'cloud', 'infrastructure', 'aws', 'azure', 'sre', 'reliability', 'systems'],
        'AI/ML': ['machine learning', 'ai', 'ml', 'deep learning', 'artificial intelligence', 'computer vision', 'deep learning', 'nlp', 'reinforcement learning'],
        'Data Science': ['data', 'analytics', 'statistics', 'sql',],
        'Embedded': ['embedded', 'firmware', 'hardware', 'iot'],
        'Security': ['security', 'cybersecurity', 'infosec', 'cryptography'],
        'Research': ['research', 'r&d', 'scientist', 'phd'],
        'Product/TPM': ['product', 'program manager', 'tpm', 'technical program']
    }
    
    for category, category_keywords in keywords.items():
        if any(keyword in title for keyword in category_keywords):
            return category
    
    return 'Other'  # Default category

def determine_sponsorship(title):
    """Determine sponsorship status based on title indicators"""
    if "🛂" in title:
        return "No Sponsorship Available"
    elif "🇺🇸" in title:
        return "Requires U.S. Citizenship"
    else:
        return "Other"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    post_opportunities.start()
    
    '''
    # Debug: Print all guilds (servers) the bot is in
    print("\nServers the bot can see:")
    for guild in bot.guilds:
        print(f"Server: {guild.name}")
        
        # Debug: Print all channels in each server
        print("Channels in this server:")
        for channel in guild.channels:
            print(f"- {channel.name}: {channel.id}")
    '''
    
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        print(f'\nFound channel: {channel.name}')
    else:
        print(f'\nCould not find channel with ID {CHANNEL_ID}')



@bot.command(name='latest')
async def latest_opportunities(ctx):
    try:
        db = OpportunityDatabase()
        opportunities = db.get_latest_opportunities(5)
        
        if not opportunities:
            await ctx.send("No opportunities available at the moment.")
            return

        for opp in opportunities:
            embed = create_opportunity_embed(opp)
            await ctx.send(embed=embed)
            await asyncio.sleep(1)
    except Exception as e:
        await ctx.send(f"An error occurred while fetching opportunities: {str(e)}")


@bot.command(name='bothelp')
async def help_command(ctx):
    """Show help information about bot commands"""
    embed = discord.Embed(
        title="Internship Opportunities Bot - Help",
        description="Available commands:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="!latest",
        value="Shows the 5 most recent internship opportunities",
        inline=False
    )
    embed.add_field(
        name="!help",
        value="Shows this help message",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    """Error handling for bot commands"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Use !help to see available commands.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")

# MAIN
if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
        
    except Exception as e:
        print(f"Error running bot: {str(e)}")