from gavel import app
from gavel import socketio
from gavel.models import *
from gavel.schemas import *
from gavel.constants import *
from functools import wraps
import gavel.settings as settings
import gavel.utils as utils
from flask import (
  redirect,
  render_template,
  request,
  url_for,
  json,
  jsonify,
  Response
)
from gavel import JSON
from flask_json import json_response, as_json
from collections import defaultdict

socket = socketio
from sqlalchemy import event

try:
  import urllib
except ImportError:
  import urllib3
import xlrd

import asyncio

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def async_action(f):
  @wraps(f)
  def wrapped(*args, **kwargs):
    return loop.run_until_complete(f(*args, **kwargs))
  return wrapped


ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}


@app.route('/legacy/')
@utils.requires_auth
def admin_legacy():
  annotators = Annotator.query.order_by(Annotator.id).all()
  items = Item.query.order_by(Item.id).all()
  flags = Flag.query.order_by(Flag.id).all()
  decisions = Decision.query.all()
  counts = {}
  item_counts = {}
  for d in decisions:
    a = d.annotator_id
    w = d.winner_id
    l = d.loser_id
    counts[a] = counts.get(a, 0) + 1
    item_counts[w] = item_counts.get(w, 0) + 1
    item_counts[l] = item_counts.get(l, 0) + 1
  viewed = {i.id: {a.id for a in i.viewed} for i in items}
  skipped = {}
  for a in annotators:
    for i in a.ignore:
      if a.id not in viewed[i.id]:
        skipped[i.id] = skipped.get(i.id, 0) + 1
  # settings
  setting_closed = Setting.value_of(SETTING_CLOSED) == SETTING_TRUE
  setting_stop_queue = Setting.value_of(SETTING_STOP_QUEUE) == SETTING_TRUE
  return render_template(
    'admin_legacy.html',
    annotators=annotators,
    counts=counts,
    item_counts=item_counts,
    item_count=len(items),
    skipped=skipped,
    items=items,
    votes=len(decisions),
    setting_closed=setting_closed,
    setting_stop_queue=setting_stop_queue,
    flags=flags,
    flag_count=len(flags)
  )


@app.route('/admin/')
@utils.requires_auth
def admin():
  annotators = Annotator.query.order_by(Annotator.id).all()
  items = Item.query.order_by(Item.id).all()
  flags = Flag.query.order_by(Flag.id).all()
  decisions = Decision.query.all()
  counts = {}
  item_counts = {}
  for d in decisions:
    a = d.annotator_id
    w = d.winner_id
    l = d.loser_id
    counts[a] = counts.get(a, 0) + 1
    item_counts[w] = item_counts.get(w, 0) + 1
    item_counts[l] = item_counts.get(l, 0) + 1
  viewed = {i.id: {a.id for a in i.viewed} for i in items}
  skipped = {}
  for a in annotators:
    for i in a.ignore:
      if a.id not in viewed[i.id]:
        skipped[i.id] = skipped.get(i.id, 0) + 1
  # settings
  setting_closed = Setting.value_of(SETTING_CLOSED) == SETTING_TRUE
  setting_stop_queue = Setting.value_of(SETTING_STOP_QUEUE) == SETTING_TRUE
  return render_template(
    'admin.html',
    annotators=annotators,
    counts=counts,
    item_counts=item_counts,
    item_count=len(items),
    skipped=skipped,
    items=items,
    votes=len(decisions),
    setting_closed=setting_closed,
    setting_stop_queue=setting_stop_queue,
    flags=flags,
    flag_count=len(flags)
  )


@app.route('/admin/items')
@utils.requires_auth
def admin_items():
  items = Item.query.order_by(Item.id).all()
  annotators = Annotator.query.order_by(Annotator.id).all()
  decisions = Decision.query.all()

  item_schema = ItemSchema()

  viewed = {}
  for i in items:
    viewed_holder = []
    for a in i.viewed:
      viewed_holder.append(a.id)
    viewed[i.id] = viewed_holder

  skipped = {}
  for a in annotators:
    skipped_holder = []
    for i in a.ignore:
      if a.id not in viewed[i.id]:
        skipped_holder.append(a.id)
    skipped[i.id] = skipped_holder

  item_count = len(items)

  item_counts = {}

  for d in decisions:
    a = d.annotator_id
    w = d.winner_id
    l = d.loser_id
    item_counts[w] = item_counts.get(w, 0) + 1
    item_counts[l] = item_counts.get(l, 0) + 1

  items_dumped = []

  for it in items:
    try:
      item_dumped = item_schema.dump(it)
      item_dumped.update({
        'votes': item_counts.get(it.id, 0),
        'skipped': list(set(skipped.get(it.id, [])))
      })
      items_dumped.append(item_dumped)
    except Exception as e:
      print(str(e))
      items_dumped.append({'null': 'null'})

  dump_data = {
    "items": items_dumped,
    "item_count": item_count
  }

  response = app.response_class(
    response=json.dumps(dump_data),
    status=200,
    mimetype='application/json'
  )

  return response


@app.route('/admin/flags')
@utils.requires_auth
def admin_flags():
  flags = Flag.query.order_by(Flag.id).all()
  flag_count = len(flags)

  flag_schema = FlagSchema()

  flags_dumped = []

  for fl in flags:
    flag_dumped = flag_schema.dump(fl)
    flag_dumped.update({
      'item_name': fl.item.name,
      'item_location': fl.item.location,
      'annotator_name': fl.annotator.name
      })
    flags_dumped.append(flag_dumped)

  dump_data = {
    "flags": flags_dumped,
    "flag_count": flag_count
  }

  response = app.response_class(
    response=json.dumps(dump_data),
    status=200,
    mimetype='application/json'
  )

  return response


@app.route('/admin/annotators')
@utils.requires_auth
def admin_annotators():
  annotators = Annotator.query.order_by(Annotator.id).all()
  decisions = Decision.query.all()
  annotator_count = len(annotators)

  annotator_schema = AnnotatorSchema()

  counts = {}

  for d in decisions:
    a = d.annotator_id
    w = d.winner_id
    l = d.loser_id
    counts[a] = counts.get(a, 0) + 1

  annotators_dumped = []
  
  for an in annotators:
    try:
      annotator_dumped = annotator_schema.dump(an)
      annotator_dumped.update({
        'votes': counts.get(an.id, 0)
      })
      annotators_dumped.append(annotator_dumped)
    except:
      annotators_dumped.append({'null': 'null'})
  dump_data = {
    "annotators": annotators_dumped,
    "anotator_count": annotator_count
  }

  response = app.response_class(
    response=json.dumps(dump_data),
    status=200,
    mimetype='application/json'
  )

  return response


@app.route('/admin/auxiliary')
@utils.requires_auth
def admin_live():
  annotators = Annotator.query.order_by(Annotator.id).all()
  items = Item.query.order_by(Item.id).all()
  flags = Flag.query.order_by(Flag.id).all()
  decisions = Decision.query.all()

  # settings
  setting_closed = Setting.value_of(SETTING_CLOSED) == SETTING_TRUE
  setting_stop_queue = Setting.value_of(SETTING_STOP_QUEUE) == SETTING_TRUE

  item_count = len(items)
  votes = len(decisions)
  flag_count = len(flags)

  # Calculate average sigma
  holder = 0.0
  for it in items:
    holder += it.sigma_sq
  try:
    average_sigma = holder / len(items)
  except:
    average_sigma = 0.0

  # Calculate average seen
  holder = 0
  for an in annotators:
    seen = Item.query.filter(Item.viewed.contains(an)).all()
    holder += len(seen)
  try:
    average_seen = holder / len(annotators)
  except:
    average_seen = 0

  dump_data = {
    "votes": votes,
    "setting_closed": setting_closed,
    "setting_stop_queue": setting_stop_queue,
    "flag_count": flag_count,
    "item_count": item_count,
    "average_sigma": average_sigma,
    "average_seen": average_seen
  }

  response = app.response_class(
    response=json.dumps(dump_data),
    status=200,
    mimetype='application/json'
  )

  return response


@app.route('/admin/item', methods=['POST'])
@utils.requires_auth
def item():
  action = request.form['action']
  if action == 'Submit':
    data = parse_upload_form()
    if data:
      # validate data
      for index, row in enumerate(data):
        if settings.VIRTUAL_EVENT:
          if len(row) != 6:
            return utils.user_error('Bad data: row %d has %d elements (expecting 6)' % (index + 1, len(row)))
        else:
          if len(row) != 3:
            return utils.user_error('Bad data: row %d has %d elements (expecting 3)' % (index + 1, len(row)))
      def tx():
        for row in data:
          # This is REALLY REALLY bad I know...
          # TODO: Tech Debt
          if settings.VIRTUAL_EVENT:
            row.insert(1, "N/A")
          _item = Item(*row)
          db.session.add(_item)
        db.session.commit()
      with_retries(tx)
  elif action == 'Prioritize' or action == 'Cancel':
    item_id = request.form['item_id']
    target_state = action == 'Prioritize'
    def tx():
      Item.by_id(item_id).prioritized = target_state
      db.session.commit()
    with_retries(tx)
  elif action == 'Disable' or action == 'Enable':
    item_id = request.form['item_id']
    target_state = action == 'Enable'
    def tx():
      Item.by_id(item_id).active = target_state
      db.session.commit()
    with_retries(tx)
  elif action == 'Delete':
    item_id = request.form['item_id']
    try:
      def tx():
        db.session.execute(ignore_table.delete().where(ignore_table.c.item_id == item_id))
        db.session.query(Annotator).filter(Annotator.next_id == item_id).update({Annotator.next_id: None})
        db.session.query(Annotator).filter(Annotator.prev_id == item_id).update({Annotator.prev_id: None})
        Item.query.filter_by(id=item_id).delete()
        db.session.commit()
      with_retries(tx)
    except IntegrityError as e:
      return utils.server_error(str(e))
  elif action == 'BatchDisable':
    item_ids = request.form.getlist('ids')
    error = []
    for item_id in item_ids:
      try:
        def tx():
          Item.by_id(item_id).active = False
          db.session.commit()
        with_retries(tx)
      except:
        error.append(item_id)
        def tx():
          db.session.rollback()
        with_retries(tx)
        error.append(item_id)
        continue
  elif action == 'BatchDelete':
    db.Session.autocommit = True
    item_ids = request.form.getlist('ids')
    error = []
    for item_id in item_ids:
      try:
        def tx():
          db.session.execute(ignore_table.delete().where(ignore_table.c.item_id == item_id))
          db.session.query(Annotator).filter(Annotator.next_id == item_id).update({Annotator.next_id: None})
          db.session.query(Annotator).filter(Annotator.prev_id == item_id).update({Annotator.prev_id: None})
          Item.query.filter_by(id=item_id).delete()
          db.session.commit()
        with_retries(tx)
      except Exception as e:
        error.append(str(e))
        def tx():
          db.session.rollback()
        with_retries(tx)
        error.append(item_id)
        continue
  return redirect(url_for('admin'))


@app.route('/admin/queueshutdown', methods=['POST'])
@utils.requires_auth
def queue_shutdown():
  action = request.form['action']
  annotators = Annotator.query.order_by(Annotator.id).all()
  if action == 'queue':
    for an in annotators:
      if an.active:
        an.stop_next = True
    def tx():
      Setting.set(SETTING_STOP_QUEUE, True)
      db.session.commit()
    with_retries(tx)
  elif action == 'dequeue':
    for an in annotators:
      if an.stop_next:
        an.stop_next = False
    def tx():
      Setting.set(SETTING_STOP_QUEUE, False)
      db.session.commit()
    with_retries(tx)

  return redirect(url_for('admin'))


@app.route('/admin/api/session/', methods=['GET','POST'])
@utils.requires_auth
def admin_api_session():
  setting_stop_queue = Setting.value_of(SETTING_STOP_QUEUE) == SETTING_TRUE
  setting_stop = Setting.value_of(SETTING_CLOSED) == SETTING_TRUE

  affected_annotators = []
  action = None
  key = None

  if request.method == "POST":

    key = request.form['key']
    # hard | soft

    action = request.form['action']

    # Hard shutdown
    if key == 'hard':
      # Close session
      if action == 'close':
        setting_stop = SETTING_TRUE
      # Open session
      elif action == 'open':
        setting_stop = SETTING_FALSE
      else:
        pass
      def tx():
        Setting.set(SETTING_CLOSED, setting_stop)
        db.session.commit()
      with_retries(tx)
    # Soft shutdown (await final judge submission)
    elif key == 'soft':
      annotators = Annotator.query.order_by(Annotator.id).all()
      # Queue shutdown
      if action == 'queue' and not setting_stop:
        setting_stop_queue = SETTING_TRUE
        def tx():
          for an in annotators:
            if an.active:
              an.stop_next = True
              affected_annotators.append(an.id)
          db.session.commit()
        with_retries(tx)
      # Dequeue shutdown
      elif action == 'dequeue':
        setting_stop_queue = SETTING_FALSE
        def tx():
          for an in annotators:
            if an.active:
              an.stop_next = False
              affected_annotators.append(an.id)
          db.session.commit()
        with_retries(tx)

      else:
        pass

      def tx():
        Setting.set(SETTING_STOP_QUEUE, setting_stop_queue)
        db.session.commit()
      with_retries(tx)

    try:
      socketio.emit(SESSION_UPDATED, {
        'type': "session",
        'target': {
          "hard_state": setting_stop == SETTING_TRUE,
          "soft_state": setting_stop_queue == SETTING_TRUE,
          "action": action,
          "key": key
        }
      }, namespace='/admin')
    except Exception as ignored:
      pass

  return json_response(
    hard_state=setting_stop,
    soft_state=setting_stop_queue,
    action=action,
    key=key,
    affected_annotators=affected_annotators
  )

@app.route('/admin/report', methods=['POST'])
@utils.requires_auth
def flag():
  action = request.form['action']
  if action == 'resolve':
    flag_id = request.form['flag_id']
    target_state = action == 'resolve'
    def tx():
      Flag.by_id(flag_id).resolved = target_state
      db.session.commit()
    with_retries(tx)
  elif action == 'open':
    flag_id = request.form['flag_id']
    target_state = 1 == 2
    def tx():
      Flag.by_id(flag_id).resolved = target_state
      db.session.commit()
    with_retries(tx)
  return redirect(url_for('admin'))

@app.route('/admin/api/flag', methods=['POST'])
@utils.requires_auth
def admin_api_report():
  action = request.form['action']
  flag_id = None
  target_state = None
  if action == 'resolve':
    flag_id = request.form['flag_id']
    target_state = action == 'resolve'
    def tx():
      Flag.by_id(flag_id).resolved = target_state
      db.session.commit()
    with_retries(tx)
  elif action == 'open':
    flag_id = request.form['flag_id']
    target_state = 1 == 2
    def tx():
      Flag.by_id(flag_id).resolved = target_state
      db.session.commit()
    with_retries(tx)
  
  return json_response(
    action=action,
    affected_flag=flag_id,
    state=target_state,
  )

def allowed_file(filename):
  return '.' in filename and \
         filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_upload_form():
  f = request.files.get('file')
  data = []
  if f and allowed_file(f.filename):
    extension = str(f.filename.rsplit('.', 1)[1].lower())
    if extension == "xlsx" or extension == "xls":
      workbook = xlrd.open_workbook(file_contents=f.read())
      worksheet = workbook.sheet_by_index(0)
      data = list(utils.cast_row(worksheet.row_values(rx, 0, 3)) for rx in range(worksheet.nrows) if
                  worksheet.row_len(rx) == 3)
    elif extension == "csv":
      data = utils.data_from_csv_string(f.read().decode("utf-8"))
  else:
    csv = request.form['data']
    data = utils.data_from_csv_string(csv)
  return data


@app.route('/admin/item_patch', methods=['POST'])
@utils.requires_auth
def item_patch():
  def tx():
    item = Item.by_id(request.form['item_id'])
    if not item:
      return utils.user_error('Item %s not found ' % request.form['item_id'])
    if 'location' in request.form:
      item.location = request.form['location']
    if 'name' in request.form:
      item.name = request.form['name']
    if 'description' in request.form:
      item.description = request.form['description']
    if 'tagline' in request.form:
      item.tagline = request.form['tagline']
    if 'video_reference' in request.form:
      item.video_reference = request.form['video_reference']
    if 'submission_reference' in request.form:
      item.submission_reference = request.form['submission_reference']
    if 'submission_website' in request.form:
      item.submission_website = request.form['submission_website']
    db.session.commit()
  with_retries(tx)
  return redirect(url_for('item_detail', item_id=request.form['item_id']))

@app.route('/admin/api/item_patch', methods=['POST'])
@utils.requires_auth
def admin_api_item_patch():
  item_id = request.form['item_id']
  def tx():
    item = Item.by_id(item_id)
    if not item:
      return utils.user_error('Item %s not found ' % item_id)
    if 'location' in request.form:
      item.location = request.form['location']
    if 'name' in request.form:
      item.name = request.form['name']
    if 'description' in request.form:
      item.description = request.form['description']
    db.session.commit()
  with_retries(tx)
  return json_response(

  )


@app.route('/admin/annotator_patch', methods=['POST'])
@utils.requires_auth
def annotator_patch():
  def tx():
    annotator = Annotator.by_id(request.form['annotator_id'])
    if not item:
      return utils.user_error('Annotator %s not found ' % request.form['annotator_id'])
    if 'name' in request.form:
      annotator.name = request.form['name']
    if 'email' in request.form:
      annotator.email = request.form['email']
    if 'description' in request.form:
      annotator.description = request.form['description']
    db.session.commit()
  with_retries(tx)
  return redirect(url_for('annotator_detail', annotator_id=request.form['annotator_id']))


@app.route('/admin/annotator', methods=['POST'])
@utils.requires_auth
def annotator():
  action = request.form['action']
  if action == 'Submit':
    data = parse_upload_form()
    added = []
    if data:
      # validate data
      for index, row in enumerate(data):
        if len(row) != 3:
          return utils.user_error('Bad data: row %d has %d elements (expecting 3)' % (index + 1, len(row)))
      def tx():
        for row in data:
          annotator = Annotator(*row)
          added.append(annotator)
          db.session.add(annotator)
        db.session.commit()
      with_retries(tx)
      try:
        email_invite_links(added)
      except Exception as e:
        return utils.server_error(str(e))
  elif action == 'Email':
    annotator_id = request.form['annotator_id']
    try:
      email_invite_links(Annotator.by_id(annotator_id))
    except Exception as e:
      return utils.server_error(str(e))
  elif action == 'Disable' or action == 'Enable':
    annotator_id = request.form['annotator_id']
    target_state = action == 'Enable'
    def tx():
      Annotator.by_id(annotator_id).active = target_state
      db.session.commit()
    with_retries(tx)
  elif action == 'Delete':
    annotator_id = request.form['annotator_id']
    try:
      def tx():
        db.session.execute(ignore_table.delete().where(ignore_table.c.annotator_id == annotator_id))
        db.session.execute(view_table.delete().where(view_table.c.annotator_id == annotator_id))
        Annotator.query.filter_by(id=annotator_id).delete()
        db.session.commit()
      with_retries(tx)
    except IntegrityError as e:
      return utils.server_error(str(e))
  elif action == 'BatchDisable':
    annotator_ids = request.form.getlist('ids')
    errored = []
    for annotator_id in annotator_ids:
      try:
        def tx():
          Annotator.by_id(annotator_id).active = False
          db.session.commit()
        with_retries(tx)
      except:
        def tx():
          db.session.rollback()
        with_retries(tx)
        errored.append(annotator_id)
        continue
  elif action == 'BatchDelete':
    annotator_ids = request.form.getlist('ids')
    errored = []
    for annotator_id in annotator_ids:
      try:
        def tx():
          db.session.execute(ignore_table.delete().where(ignore_table.c.annotator_id == annotator_id))
          db.session.execute(view_table.delete().where(view_table.c.annotator_id == annotator_id))
          Annotator.query.filter_by(id=annotator_id).delete()
          db.session.commit()
        with_retries(tx)
      except:
        def tx():
          db.session.rollback()
        with_retries(tx)
        errored.append(annotator_id)
        continue
  return redirect(url_for('admin'))


@app.route('/admin/setting', methods=['POST'])
@utils.requires_auth
def setting():
  key = request.form['key']
  if key == 'closed':
    action = request.form['action']
    new_value = SETTING_TRUE if action == 'Close' else SETTING_FALSE
    Setting.set(SETTING_CLOSED, new_value)
    db.session.commit()
  return redirect(url_for('admin'))


@app.route('/admin/item/<item_id>/')
@utils.requires_auth
def item_detail(item_id):
  item = Item.by_id(item_id)
  if not item:
    return utils.user_error('Item %s not found ' % item_id)
  else:
    assigned = Annotator.query.filter(Annotator.next == item).all()
    viewed_ids = {i.id for i in item.viewed}
    if viewed_ids:
      skipped = Annotator.query.filter(
        Annotator.ignore.contains(item) & ~Annotator.id.in_(viewed_ids)
      )
    else:
      skipped = Annotator.query.filter(Annotator.ignore.contains(item))
    return render_template(
      'admin_item.html',
      item=item,
      assigned=assigned,
      skipped=skipped
    )


@app.route('/admin/annotator/<annotator_id>/')
@utils.requires_auth
def annotator_detail(annotator_id):
  annotator = Annotator.by_id(annotator_id)
  if not annotator:
    return utils.user_error('Annotator %s not found ' % annotator_id)
  else:
    seen = Item.query.filter(Item.viewed.contains(annotator)).all()
    ignored_ids = {i.id for i in annotator.ignore}
    if ignored_ids:
      skipped = Item.query.filter(
        Item.id.in_(ignored_ids) & ~Item.viewed.contains(annotator)
      )
    else:
      skipped = []
    return render_template(
      'admin_annotator.html',
      annotator=annotator,
      login_link=annotator_link(annotator),
      seen=seen,
      skipped=skipped
    )


def annotator_link(annotator):
  return url_for('login', secret=annotator.secret, _external=True)

@async_action
async def email_invite_links(annotators):
  if settings.DISABLE_EMAIL or annotators is None:
    return
  if not isinstance(annotators, list):
    annotators = [annotators]

  emails = []
  for annotator in annotators:
    link = annotator_link(annotator)
    raw_body = settings.EMAIL_BODY.format(name=annotator.name, link=link)
    body = '\n\n'.join(utils.get_paragraphs(raw_body))
    emails.append((annotator.email, settings.EMAIL_SUBJECT, body))

  utils.send_emails.apply_async(args=[emails])
