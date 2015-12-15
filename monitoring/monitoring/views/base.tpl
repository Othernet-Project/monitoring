<!doctype html>
<html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        ## Translators, used in page title
        <title><%block name="title">${_('Outernet Service Status')}</%block></title>
        <meta name="viewport" content="initial-scale=1, maximum-scale=1, user-scalable=no" />
        <link rel="stylesheet" href="${assets['css/base']}">
        <%block name="extra_head"/>
    </head>
    <body>
        <%block name="header">
            <header class="menu">
            <h1><a href="/">${_('Outernet service status')}</a></h1>
            <p class="other-pages">

            </p>
            </header>
        </%block>

        <div class="body">
        <%block name="main">
            ${self.body()}
        </%block>
        </div>

        <%block name="extra_scripts"/>
    </body>
</html>
