# Bike and Bike Part Datbase

A web based application for storing information on bicycles and their components.
Helps users keep track of bikes they own or are interested in, along with a description,
manufacturer, and price. It also allows users to store information about the components.


## Getting Started

To conduct the queries, follow the prerequisites and installing instructions
below. The project uses Python2.7.15, Vagrant, which is a linux-vased virtual
machine, and SQLite database running on the virtual machine.

First thing is to clone the repository.

```
git clone https://github.com/mamelmahdy/fullstack-nanodegree-vm.git
```


### Prerequisites

First setup the linux-based virtual machine [Vagrant](https://www.vagrantup.com/)
and [VirtualBox](https://www.virtualbox.org/wiki/Download_Old_Builds_5_1)

You will need to bring the vagrant machine up and SSH into it, so in a terminal
or git bash within the vagrant folder of the project directory run as follows

```
vagrant up
vagrant ssh
```

Once in the vagrant machine, make sure that Vagrant has Python already installed

```
python3 --version
```

The project folder containing the web application files can be accessed in the vargant VM by running.

```
cd /vagrant/catalog
```

This project requires a few python libraries, which should be preloaded on the
vagrant machine but if not (python reports missing modules), then install the
libraries as follows.

```
sudo pip install flask
sudo pip install sqlalchemy
sudo pip install oauth2client
```

### Installing

The project requires Bike and Bike Part database found in the project directory 'bike.db'.

If you wish to start with a new database. Delete the database file 'bike.db' and use the database
setup python file to make a new database file in the project directory.

```
python database_setup.py
```

To monitor the database file, you can use DB Browser for SQLite found [here](http://sqlitebrowser.org/).

## Running the tests

To run the server use python to run the project file 'application.py' as follows.
The server listens on port 8000, so make sure you have no other web applications
using that port, or any firewall rules blocking use of that port.

```
python application.py
```

### Signup and Logging in

Once the server is running, point a web browser to http://localhost:8000/login
to login using third party providers (Google and Facebook) or signup with an account
that saves your user profile in the bike database.

### Adding Bikes to the Database

Once logged in, you can view a list of bikes already in the database. If you are
using your own new database, then proceed to adding a bike and provide the name,
manufacturer, a short description, and price of the bike.

### Adding Bike Parts to the Database

Click on a bike in the list to edit the components that the bike has. For instance
you can add the name, description, and type (i.e. frame, fork, seat, tires).

### Editing Bike and Bike Parts

There are links to edit or delete bikes and bike parts from the database too! Only
the user that added the bike and bike part will be able to do this however.

## Authors

* **Mohamed**

## Acknowledgments

* Udacity!
