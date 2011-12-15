from django.db import models
from django.utils.itercompat import is_iterable
from django.db.models.signals import class_prepared

_wait_triggers = []

def _connect_trigger(sender, **kwargs):
   connected = []
   for trigger in _wait_triggers:
       model = models.get_model(*trigger.sender_model.split('.', 1))
       if model:
           trigger.sender = model
           trigger.wait_connect = False
           trigger.connect()
           connected.append(trigger)

   for trigger in connected:
       _wait_triggers.remove(trigger)

class_prepared.connect(_connect_trigger)

class Trigger(object):
    def __init__(self, do, on, field_name, sender, sender_model, commit, field_holder_getter):
        self.freeze = False
        self.field_name = field_name
        self.commit = commit
        #sender has priority
        if sender is not None:
            self.sender_model = sender

        #waiting for models defined as strings
        if isinstance(sender_model, basestring):
            model = models.get_model(*self.sender_model.split(".", 1))
            if model is None:
               self.wait_connect = True
               _wait_triggers.append(self)
            else:
                self.sender_model = model

        self.sender = self.sender_model

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

        objects = self.field_holder_getter(instance)
        if not is_iterable(objects):
            objects = [objects]

        for obj in objects:
            if obj:
                setattr(obj, self.field_name, self.do(obj, instance, signal, kwargs))
                if self.commit:
                    obj.save()
