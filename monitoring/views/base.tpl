<!doctype html>
<html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        ## Translators, used in page title
        <title><%block name="title">Outernet Service Status</%block></title>
        <link rel="stylesheet" href="${assets['css/main']}" />
        <meta name="viewport" content="initial-scale=1, maximum-scale=1, user-scalable=no" />
        % if redirect_url is not UNDEFINED:
        <meta http-equiv="refresh" content="${REDIRECT_DELAY}; url=${redirect_url}" />
        % endif
        <%block name="extra_head"/>
    </head>
    <body>
        <%block name="header">
        <header class="menu">
            <div class="menu-subblock">
                <a class="logo" href="${url('status:main')}"><span lang="en">Outernet</span></a>
            </div>
            <div class="menu-block-right">
                <nav id="nav" class="menu-subblock toolbar">
                    <a href="http://www.outernet.is/" class="homepage"><span class="label">${_("Outernet Homepage")}</span></a>
                </nav>
                <div class="hamburger">
                    <a href="#nav">Site menu</a>
                </div>
            </div>
        </header>
        </%block>

        <div class="section body">
        <%block name="main">
            ${self.body()}
        </%block>
        </div>

        <%block name="footer">
        <footer>
            <p class="logo"><span lang="en">Outernet</span>: ${_("Humanity's public library")}</p>
            <p class="copyright">2014-2015 <span lang="en">Outernet Inc</span></p>
        </footer>
        </%block>

        <%block name="extra_scripts"/>
    </body>
</html>
