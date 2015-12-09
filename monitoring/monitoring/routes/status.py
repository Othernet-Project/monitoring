from librarian_core.contrib.templates.renderer import view


@view('status')
def show_status():
    # fetch report from database and return status page
    return dict()
