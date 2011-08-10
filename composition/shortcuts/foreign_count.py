from composition.base import CompositionField
from django.db import models

class ForeignCountField(CompositionField):
    def __init__(self, model, link_back_name, link_to_foreign_name, filter=None, native=None, signal=None, verbose_name=None):
        self.model = model
        if isinstance(filter, dict):
            self.do = lambda object, foreign, signal, kwargs: getattr(object, link_to_foreign_name).filter(**filter).count()
        elif filter is not None:
            self.do = lambda object, foreign, signal, kwargs: getattr(object, link_to_foreign_name).filter(filter).count()
        else:
            self.do = lambda object, foreign, signal, kwargs: getattr(object, link_to_foreign_name).count()
        self.link_back_name = link_back_name
        self.native = native or models.PositiveIntegerField(default=0, db_index=True, verbose_name=verbose_name)
        self.signal = signal or (models.signals.post_save, models.signals.post_delete)
    
        self.internal_init(
            native = self.native,
            trigger = dict(
                on = self.signal,
                sender_model = self.model,
                do = self.do,
                field_holder_getter = self.instance_getter
            )
        )

    def instance_getter(self, foreign):
        ''' Return instance getter with special check for generic relation '''
        try:
            instance = getattr(foreign, self.link_back_name)
            if not instance and self.link_back_name == 'content_object':
                instance = foreign.content_type.get_object_for_this_type(id=foreign.object_id)
            return instance
        except Exception:
            return False
