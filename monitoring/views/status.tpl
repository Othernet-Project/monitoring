<%inherit file='base.tpl'/>

<%block name="extra_head">
<meta http-equiv="refresh" content="300; /">
</%block>

<%block name="main">
<div class="h-bar">
    <h2>${_('Outernet Service Status')}</h2>
    <p>${_('This page automatically refreshes every 5 minutes.')}</p>
</div>
<div class="full-page-form status">
    <div class="report-section overview">
        <p><strong>${_("Updated")}:</strong>&nbsp;<span>${last_check or _("Unknown")}</span></p>
        <table>
            <tr>
                <th>${_("Satellite")}</th>
                <th>${_("Status")}</th>
                <th>${_("Errors")}</th>
                <th>${_("Bitrate")}</th>
                <th>${_("Devices")}</th>
            </tr>
            % for sat_name in satellites:
            <tr>
                <% current_sat = status.get(sat_name, {}) %>
                % if current_sat:
                    % if current_sat['status'] == 'CRITICAL':
                    <% health = h.SPAN('', _class='health bad') %>
                    % elif current_sat['status'] == 'WARNING':
                    <% health = h.SPAN('', _class='health warning') %>
                    % elif current_sat['status'] == 'NORMAL':
                    <% health = h.SPAN('', _class='health good') %>
                    % else:
                    <% health = h.SPAN('', _class='health neutral') %>
                    % endif
                % else:
                    <% health = h.SPAN('', _class='health neutral') %>
                % endif
                <td>${sat_name}</td>
                <td>${health}</td>
                <td>${round(current_sat.get('error_rate', 0) * 100)}%</td>
                <td>${h.hsize(current_sat.get('bitrate', 0), unit='bps')}</td>
                <td>${current_sat.get('clients', 0)}</td>
            </tr>
            % endfor
        </table>
    </div>
</div>
</%block>
