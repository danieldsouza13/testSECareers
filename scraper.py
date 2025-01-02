from pymongo import MongoClient
import os
from datetime import datetime
from bot import OpportunityDatabase
from bot import fetch_opportunities

def scrape_and_store():
    try:
        client = MongoClient(os.environ['MONGODB_URI'])
        db = client['SECareers']
        opportunities = db['Opportunity Listings']
        
        new_opportunities = fetch_opportunities()
        
        for opp in new_opportunities:
            if not OpportunityDatabase().opportunity_exists(opportunities, opp):
                opp['timestamp'] = datetime.now()
                opportunities.insert_one(opp)
                
    except Exception as e:
        print(f"Error in scraper: {e}")

if __name__ == "__main__":
    scrape_and_store()
