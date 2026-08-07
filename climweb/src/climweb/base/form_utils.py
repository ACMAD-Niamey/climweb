def effective_clean_name(field):
    """
    A form field's stored clean_name can be blank - e.g. a row created via
    bulk_create() or a data migration bypasses AbstractFormField.save(),
    which is the only place clean_name gets generated. Wagtail's own
    FormBuilder.formfields already tolerates this by falling back to
    field.get_field_clean_name() (wagtail.contrib.forms.forms.FormBuilder),
    so the live form renders and submits fine under that recomputed key.
    Admin-side code that reads field.clean_name directly instead doesn't get
    that fallback, so it looks up the wrong (empty) key and shows a blank
    value for data that's actually there under the recomputed key - use this
    everywhere a form field needs to be resolved to its submitted data key.

    Lives in its own module (rather than base.forms) because base.mixins -
    imported by base.models.abstracts - needs it too, and base.forms itself
    imports from base.models, which would otherwise be a circular import.
    """
    return field.clean_name or field.get_field_clean_name()
