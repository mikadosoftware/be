import turbogears
from turbogears import controllers
import cherrypy
from libbe.bugdir import tree_root, cmp_severity, new_bug, new_comment
from libbe import names
from config import projects
from prest import PrestHandler, provide_action

def project_tree(project):
    try:
        return tree_root(projects[project][1])
    except KeyError:
        raise Exception("Unknown project %s" % project)

def comment_url(project, bug, comment):
    return turbogears.url("/project/%s/bug/%s/comment/%s" %
                          (project, bug, comment))

class Comment(PrestHandler):
    @provide_action("action", "New comment")
    def new_comment(self, comment_data, comment, *args, **kwargs):
        bug_tree = project_tree(comment_data['project'])
        bug = bug_tree.get_bug(comment_data['bug'])
        comment = new_comment(bug, "")
        comment.save()
        raise cherrypy.HTTPRedirect(comment_url(comment=comment.uuid, 
                                    **comment_data))

    @provide_action("action", "Update")
    def update(self, comment_data, comment, comment_body, *args, **kwargs):
        comment.body = comment_body
        comment.save()
        raise cherrypy.HTTPRedirect(bug_url(comment_data['project'], 
                                            comment_data['bug']))

    def instantiate(self, project, bug, comment):
        bug_tree = project_tree(project)
        bug = bug_tree.get_bug(bug)
        return bug.get_comment(comment)

    def dispatch(self, comment_data, comment, *args, **kwargs):
        return self.edit_comment(comment_data['project'], comment)

    @turbogears.expose(html="beweb.templates.edit_comment")
    def edit_comment(self, project, comment):
        return {"comment": comment, "project_id": project}

class Bug(PrestHandler):
    comment = Comment()
    @turbogears.expose(html="beweb.templates.edit_bug")
    def index(self, project, bug):
        return {"bug": bug, "project_id": project}
    
    def dispatch(self, bug_data, bug, *args, **kwargs):
        if bug is None:
            return self.list(bug_data['project'], **kwargs)
        else:
            return self.index(bug_data['project'], bug)

    @turbogears.expose(html="beweb.templates.bugs")
    def list(self, project, sort_by=None, show_closed=False, action=None):
        if action == "New bug":
            self.new_bug()
        if show_closed == "False":
            show_closed = False
        bug_tree = project_tree(project)
        bugs = list(bug_tree.list())
        if sort_by is None:
            def cmp_date(bug1, bug2):
                return -cmp(bug1.time, bug2.time)
            bugs.sort(cmp_date)
            bugs.sort(cmp_severity)
        return {"project_id"      : project,
                "project_name"    : projects[project][0],
                "bugs"            : bugs,
                "show_closed"     : show_closed,
               }

    @provide_action("action", "New bug")
    def new_bug(self, bug_data, bug, **kwargs):
        bug = new_bug(project_tree(bug_data['project']))
        bug.save()
        raise cherrypy.HTTPRedirect(bug_url(bug_data['project'], bug.uuid))

    @provide_action("action", "Update")
    def update(self, bug_data, bug, status, severity, summary, action):
        bug.status = status
        bug.severity = severity
        bug.summary = summary
        bug.save()
        raise cherrypy.HTTPRedirect(bug_list_url(bug_data["project"]))

    def instantiate(self, project, bug):
        return project_tree(project).get_bug(bug)

    @provide_action("action", "New comment")
    def new_comment(self, bug_data, bug, *args, **kwargs):
        return self.comment.new_comment(bug_data, comment=None, *args, 
                                         **kwargs)


def project_url(project_id=None):
    project_url = "/project/"
    if project_id is not None:
        project_url += "%s/" % project_id
    return turbogears.url(project_url)

def bug_url(project_id, bug_uuid=None):
    bug_url = "/project/%s/bug/" % project_id
    if bug_uuid is not None:
        bug_url += "%s/" % bug_uuid
    return turbogears.url(bug_url)

def bug_list_url(project_id, show_closed=False):
    bug_url = "/project/%s/bug/?show_closed=%s" % (project_id, 
                                                   str(show_closed))
    return turbogears.url(bug_url)


class Project(PrestHandler):
    bug = Bug()
    @turbogears.expose(html="beweb.templates.projects")
    def dispatch(self, project_data, project, *args, **kwargs):
        if project is not None:
            raise cherrypy.HTTPRedirect(bug_url(project)) 
        else:
            return {"projects": projects}

    def instantiate(self, project):
        return project


class Root(controllers.Root):
    prest = PrestHandler()
    prest.project = Project()
    @turbogears.expose()
    def index(self):
        raise cherrypy.HTTPRedirect(project_url()) 
    @turbogears.expose()
    def default(self, *args, **kwargs):
        return self.prest.default(*args, **kwargs)
