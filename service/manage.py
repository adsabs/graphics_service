import re
import sys
from flask.ext.script import Manager, Command, Option
from flask.ext.migrate import Migrate, MigrateCommand
from models import db, GraphicsModel
from app import create_app
from utils import get_identifiers
import time
from datetime import datetime
from collections import defaultdict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

app = create_app()
migrate = Migrate(app, db)
manager = Manager(app)

app.config['SQLALCHEMY_DATABASE_URI'] = app.config[
    'SQLALCHEMY_BINDS']['graphics']

# By default the harvester looks at the current and previous year
now = datetime.now()
default_year = "%s-%s" % (now.year - 1, now.year)
# We will allow both arXiv categories and their ADS bibstem equivalents
# Create mappings in both directions
categories = app.config.get('GRAPHICS_PUBSETS').get('arXiv')
bibstems = map(lambda a: re.sub(r"\W", ".", "%-5s" % a), categories)
category2bibstem = {}
bibstem2category = {}
for a in map(None, categories, bibstems):
    category2bibstem[a[0]] = a[1]
    bibstem2category[a[1]] = a[0]


class CreateDatabase(Command):

    """
    Creates the database based on models.py
    """

    def run(self):
        with create_app().app_context():
            db.create_all()


class UpdateDatabase(Command):

    """
    Updates the graphics database, given the input parameters
    """

    option_list = (
        Option('--force', '-f', dest='force',
               default=False, action="store_true"),
        Option('--identifier', '-i', dest='identifier'),
        Option('--year', '-y', dest='year', default=default_year),
        Option('--journal', '-j', dest='bibstem'),
        Option('--set', '-s', dest='set', default='IOP, arXiv')
    )

    def run(self, **kwargs):
        set2journal = app.config.get('GRAPHICS_PUBSETS')
        journal2set = dict((v, k) for k in set2journal for v in set2journal[k])
        identifiers = defaultdict(list)
        if kwargs.get('identifier'):
            sys.stderr.write('Processing %s\n'%kwargs.get('identifier'))
            # Explicit specification of an identifier implies "forced"
            kwargs['force'] = True
            for identifier in kwargs.get('identifier').split(','):
                # Get the bibcode or arXiv ID associated with the identifier
                if identifier[:4].isdigit():
                    bibstem = identifier[4:13]
                    year    = identifier[:4]
                    source  = ""
                    res = get_identifiers(bibstem, year, source)
                    try:
                        ident = [r for r in res if r['bibcode'] == identifier][0]
                    except:
                        ident = {'bibcode': identifier}
                else:
                    bibstem = 'arXiv'
                    source  = 'arXiv'
                    if identifier.find('arXiv') > -1:
                        year = "20%s" % identifier.split(':')[1][:2]
                    else:
                        yy = identifier.split('/')[1][:2]
                        if int(yy) > 80:
                            year = "19%s" % yy
                        else:
                            year = "20%s" % yy
                    res = get_identifiers(bibstem, year, source)
                    try:
                        ident = [r for r in res if identifier in r.values()][0]

                    except IndexError:
                        ident = {}
                for pset in set2journal:
                    if [j for j in set2journal[pset] if j in identifier]:
                        identifiers[pset].append(ident)
        else:
            try:
                year = kwargs.get('year')
            except ValueError:
                year = default_year
            if kwargs.get('bibstem'):
                for bibstem in kwargs.get('bibstem').split(','):
                    sys.stderr.write('Processing %s (%s)\n' % (bibstem, year))
                    if bibstem2category.get(bibstem, bibstem) in journal2set:
                        pset = journal2set.get(
                            bibstem2category.get(bibstem, bibstem))
                        bibstem = category2bibstem.get(bibstem, bibstem)
                        identifiers[pset] += get_identifiers(bibstem, year,
                                                             pset)
            elif kwargs.get('set'):
                for pset in kwargs.get('set').split(','):
                    sys.stderr.write('Processing %s (%s)\n' % (pset, year))
                    if pset == 'arXiv':
                        # For arXiv as set, we don't need to work with
                        # bibstems
                        identifiers[pset] = get_identifiers(pset, year, pset)
                    else:
                        for bibstem in set2journal.get(pset, []):
                            identifiers[pset] += get_identifiers(bibstem, year,
                                                                 pset)
        with create_app().app_context():
            stime = time.time()
            nrecs = db.session.query(GraphicsModel).count()
            sys.stderr.write('Number of records (before): %s\n'%nrecs)
            rec_num = 0
            for pset, ids in identifiers.items():
                rec_num += len(ids)
                try:
                    gmethod = "process_%s_graphics" % pset
                    process_graphics = getattr(
                        __import__("utils", fromlist=[gmethod]), gmethod)
                    res = process_graphics(ids, force=kwargs.get('force'))
                except:
                    pass
            nrecs = db.session.query(GraphicsModel).count()
            sys.stderr.write('Number of records (after): %s\n'%nrecs)
            duration = time.time() - stime
            sys.stderr.write('Processed %s records in %s seconds\n'%(rec_num, duration))

manager.add_command('db', MigrateCommand)
manager.add_command('createdb', CreateDatabase())
manager.add_command('updatedb', UpdateDatabase())

if __name__ == '__main__':
    manager.run()
