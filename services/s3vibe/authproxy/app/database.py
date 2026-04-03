from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from .models import Base


class DatabasePool:
    
    def __init__(self, database_url, minconn=2, maxconn=10):
        self.database_url = database_url
        
        self.engine = create_engine(
            database_url,
            pool_size=minconn,
            max_overflow=maxconn - minconn,
            pool_pre_ping=True,
            echo=False
        )
        
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
    
    @contextmanager
    def get_session(self):
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        if self.engine:
            self.engine.dispose()
