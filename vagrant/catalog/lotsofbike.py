from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Bike, BikePart, User

engine = create_engine('sqlite:///bike.db')

Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create dummy user
User1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()

# Bike
bike = Bike(user_id=1, name="Orca M20i", description="The Orbea Orca M20i Performance Road Bike is ready to conquer the roads and keep you moving for miles! It is made out of a full carbon frame for lightweight durability and an OME carbon fork gives you a responsive feel for the road. Shimano Shifters and derailleurs ensure you get into gear easily. When you're looking for adventure The Orbea Orca M20i Performance Road Bike has you covered!" ,
                manufacturer= "Orbea", price= '$2999.81')

session.add(bike)
session.commit()

Item1 = BikePart(user_id=1, name="Frame", description="Orbea Orca carbon OME, monocoque,tapered 1-1/8in - 1,5in, PF 86mm, powermeter compatible, brake internal cable routing, EC/DC compatible, 130mm rear spacing, 27,2mm seat tube",
                     manufacturer="Orbea", bike=bike)

session.add(Item1)
session.commit()

print "Populated Bike Database!"
