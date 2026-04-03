import os
import sys
from twisted.internet import reactor
from twisted.web import server
from twisted.python import log
from dotenv import load_dotenv

from app.routes import RootResource
from app.database import DatabasePool

def main():
    load_dotenv()
    
    log.startLogging(sys.stdout)
    
    db_url = os.getenv('DATABASE_URL', 'postgresql://storageadmin:storagepass@postgres:5432/storage')
    db_pool = DatabasePool(db_url)
    
    root = RootResource(db_pool)
    
    site = server.Site(root)
    
    port = int(os.getenv('PORT', 8000))
    reactor.listenTCP(port, site)
    
    reactor.run()

if __name__ == '__main__':
    main()
