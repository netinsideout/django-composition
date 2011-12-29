from django.db import models
from django.utils.itercompat import is_iterable
from django.db.models.signals import class_prepared
from django.core.exceptions import ObjectDoesNotExist

_wait_triggers = {}

def _connect_trigger(sender, **kwargs):
   if sender.__name__ in _wait_triggers.keys():
       trigger = _wait_triggers[sender.__name__]
       trigger.sender = sender
       trigger.wait_connect = False
       trigger.connect()
       del _wait_triggers[sender.__name__]
class_prepared.connect(_connect_trigger)

class Trigger(object):
    def __init__(self, do, on, field_name, sender, sender_model, commit, field_holder_getter):
        self.freeze = False
        self.field_name = field_name
        self.commit = commit
        self.wait_connect = False
        #sender has priority
        if sender is not None:
            sender_model = sender

        #waiting for models defined as strings
        if isinstance(sender_model, basestring):
            model = models.get_model(*sender_model.split(".", 1), seed_cache=False)
            if model is None:
               self.wait_connect = True
               _wait_triggers[sender_model.split(".", 1)[1]] = self
            else:
                sender_model = model

        self.sender = sender_model

        if not do:
            raise ValueError("`do` action not defined for trigger")
        self.do = do

        if not is_iterable(on):
            on = [on]
        self.on = on

        self.field_holder_getter = field_holder_getter

    def connect(self):
        """
           Connects trigger's handler to all of its signals
        """
        for signal in self.on:
            if self.sender is not None:
                signal.connect(self.handler, sender=self.sender)

    def handler(self, signal, instance=None, **kwargs):
        """
            Signal handler
        """
        if self.freeze:
            return

        try:
            objects = self.field_holder_getter(instance)
        except ObjectDoesNotExist:
            return

        if not is_iterable(objects):
            objects = [objects]

        for obj in objects:
            if obj:
                setattr(obj, self.field_name, self.do(obj, instance, signal, kwargs))
                if self.commit:
                    obj.save()
