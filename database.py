from pymongo import MongoClient
from datetime import datetime
import os

class OpportunityDatabase:
    def __init__(self):
        self.client = MongoClient(
            os.environ['MONGODB_URI'],
            serverSelectionTimeoutMS=5000,
            retryWrites=True,
            maxPoolSize=50
        )
        self.db = self.client['SECareers']
        self.opportunities = self.db['Opportunity Listings']
        
        self.opportunities.create_index([
            ("company", 1),
            ("title", 1),
            ("location", 1),
            ("date_posted", 1),
            ("terms", 1),
            ("sponsorship", 1)
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
