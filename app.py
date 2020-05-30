#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
import collections
import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from flask_migrate import Migrate
from forms import *
import datetime
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate=Migrate(app,db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'venues'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(500))    
    website = db.Column(db.String(500))
    seeking_talent = db.Column(db.Boolean,default=False)
    seeking_description=db.Column(db.String(120))
    genres = db.Column(db.String(120))
    shows=db.relationship('Show',backref='venue',lazy=True)


class Artist(db.Model):
    __tablename__ = 'artists'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))  
    seeking_venue=db.Column(db.Boolean,default=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(500))
    website = db.Column(db.String(500))
    seeking_description=db.Column(db.String(500))
    shows=db.relationship('Show',backref='artist',lazy=True)


class Show(db.Model):
  __tablename__='shows'
  id = db.Column(db.Integer, primary_key=True)
  artist_id=db.Column(db.Integer,db.ForeignKey('artists.id'),nullable=False)
  venue_id=db.Column(db.Integer,db.ForeignKey('venues.id'),nullable=False)
  start_time=db.Column(db.DateTime)



#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():  
  return render_template('pages/home.html')


#-------------------Venues-------------------#

@app.route('/venues')
def venues():
  # gruop venues based on area
  # **need every single record. Hence, cant use group by
  venues=Venue.query.order_by(Venue.state,Venue.city).all()  
  data=[]
  for d in venues:
    if len(data)==0 or data[-1]['city']!=d.city or data[-1]['state']!=d.state:
      newdata={}
      newdata['city']=d.city
      newdata['state']=d.state
      newdata['venues']=[{'id':d.id,'name':d.name,'num_upcoming_shows':0}]
      data.append(newdata)
    else:
      data[-1]['venues'].append({'id':d.id,'name':d.name,'num_upcoming_shows':0})

  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  response={}
  response['count']=0
  response['data']=[]
  search_term=request.form.get('search_term', '')
  matching=Venue.query.filter(Venue.name.ilike('%'+search_term+'%')).all()
  for match in matching:
    d={}
    d['id']=match.id
    d['name']=match.name
    d["num_upcoming_shows"]=Show.query.filter(Show.start_time>=datetime.datetime.now()).filter(Show.venue_id==match.id).count()

    response['data'].append(d)
    response['count']+=1

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  venue=Venue.query.get(venue_id)
  venue.genres= venue.genres.split('#')[1:]

  # get shows information
  venue_shows=Show.query.filter(Show.venue_id==venue_id).all()
  venue.upcoming_shows=[]
  venue.upcoming_shows_count=0
  for show in venue_shows:
    if show.start_time>datetime.datetime.now():
      info={}
      info['artist_id']=show.artist_id
      info['artist_name']=show.artist.name
      info['artist_image_link']=show.artist.image_link
      info['start_time']=datetime.datetime.strftime(show.start_time,'%Y-%m-%d %H:%M:%S')
      venue.upcoming_shows.append(info)
      venue.upcoming_shows_count+=1
  venue.past_shows_count=len(venue_shows)-venue.upcoming_shows_count
  
  return render_template('pages/show_venue.html', venue=venue)


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  # show form for new venue
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # create Venue
  msg=''
  try:    
    d=request.form.to_dict()
    if len(d['seeking_description'])>0:
      d['seeking_talent']=True
    
    #encode genre to single string
    genre_list=request.form.getlist('genres')
    s=''
    for genre in genre_list:
      s+='#'+genre
    d['genres']=s
    
    data =Venue(**d)
    db.session.add(data)
    db.session.commit()
    msg='Venue ' + request.form['name'] + ' was successfully listed!'
  except:
    db.session.rollback()
    msg='An error occurred.'
  finally:
    db.session.close()  

  # flash status message
  flash(msg)

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  try:
    data=Venue.query.get(venue_id)
    db.session.delete(data)
    db.session.commit()
  except:
    db.session.rollback()
  finally:
    db.session.close() 

  return 

#-------------------Artists-------------------#

@app.route('/artists')
def artists():
  return render_template('pages/artists.html', artists=Artist.query.all())

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  response={}
  response['count']=0
  response['data']=[]
  search_term=request.form.get('search_term', '')
  matching=Artist.query.filter(Artist.name.ilike('%'+search_term+'%')).all()
  for match in matching:
    d={}
    d['id']=match.id
    d['name']=match.name
    d["num_upcoming_shows"]=Show.query.filter(Show.artist_id==match.id).filter(Show.start_time>datetime.datetime.now()).count()
    response['data'].append(d)
    response['count']+=1

  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id
  # replace with real venue data from the venues table, using venue_id
 
  artist=Artist.query.get(artist_id) 
  artist.genres=artist.genres.split('#')[1:]

  # find shows 
  artist.past_shows=[]
  artist.upcoming_shows=[]
  artist.upcoming_shows_count=0
  artist.past_shows_count=0
  artist_shows=Show.query.filter_by(artist_id=artist_id)
  for s in artist_shows:
    d={}
    d['id']=s.venue.id
    d['venue_name']=s.venue.name
    d['venue_image_link']=s.venue.image_link
    d['start_time']=datetime.datetime.strftime(s.start_time,'%Y-%m-%d %H:%M:%S')
    if s.start_time>=datetime.datetime.now():
      artist.upcoming_shows.append(d)
      artist.upcoming_shows_count+=1
    else:
      artist.past_shows.append(d)
      artist.past_shows_count+=1
  
  
  return render_template('pages/show_artist.html', artist=artist)

#  Update
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  # populate form with fields from artist with ID <artist_id>
  artist=Artist.query.get(artist_id) 
  artist.genres=artist.genres.split('#')[1:]
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
    
  # unpack dictionary to object  
  d=request.form.to_dict()
  if len(d['seeking_description'])>0:
    d['seeking_venue']=True
  
  # update object based on form input
  artist=Artist.query.get(artist_id) 
  for key,value in d.items():
    setattr(artist,key,value)

  genre_list=request.form.getlist('genres')
  s=''
  for genre in genre_list:
    s+='#'+genre
  artist.generes=s
  db.session.commit()
  db.session.close()  

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm() 
  return render_template('forms/edit_venue.html', form=form, venue=Venue.query.get(venue_id))

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  
  d=request.form.to_dict()
  if len(d['seeking_description'])>0:
    d['seeking_venue']=True
  

  #encode genre to single string
  genre_list=request.form.getlist('genres')
  s=''
  for genre in genre_list:
    s+='#'+genre
  d['genres']=s

  # update object based on form input
  venue=Venue.query.get(venue_id) 
  for key,value in d.items():
    setattr(venue,key,value)
  db.session.commit()
  db.session.close()  

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # insert form data as a new Venue record in the db, instead
  # modify data to be the data object returned from db insertion

  msg=''
  try:
    # unpack dictionary to object  
    d=request.form.to_dict()

    # check if seeking description is not empty
    if len(d['seeking_description'])>0:
      d['seeking_venue']=True

    #encode genre to single string
    genre_list=request.form.getlist('genres')
    s=''
    for genre in genre_list:
      s+='#'+genre
    d['genres']=s
    
    artist = Artist(**d)
    db.session.add(artist)
    db.session.commit()
    msg='Artist ' + request.form['name'] + ' was successfully listed!'

  except:
    db.session.rollback()
    msg='An error occurred. Artist '
  finally:
    db.session.close()  
    flash(msg)

  return render_template('pages/home.html')


#-----------Shows-----------#

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  shows=Show.query.all()  
  data=[]
  for show in shows:
    d={}
    d['venue_id']=show.venue_id
    d['venue_name']=show.venue.name
    d['artist_id']=show.artist_id
    d['artist_name']=show.artist.name
    d['artist_image_link']=show.artist.image_link
    d['start_time']=datetime.datetime.strftime(show.start_time,'%Y-%m-%d %H:%M:%S')
    data.append(d)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  msg=''
  try:
    d=request.form.to_dict()
    show=Show(**d)
    db.session.add(show)
    db.session.commit()
    msg='Show was successfully listed!'
  except:
    msg='An error occurred. Show could not be listed.'
  finally:
    db.session.close()
    flash(msg)

  return render_template('pages/home.html')



#----------------------------------------------------------------------------#
# Error handling
#----------------------------------------------------------------------------#
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

  

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
