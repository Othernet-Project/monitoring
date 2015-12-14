<%inherit file='base.tpl'/>

<%block name="extra_head">
    <meta http-equiv="refresh" content="300; url=/">
    <link rel="stylesheet" href="${assets['css/status']}">
</%block>

<%block name="main">
<div class="status">
    <div class="note">
        <p>${_('This page automatically refreshes every 5 minutes.')}</p>
        <p><strong>${_("Updated")}:&nbsp;<span>${last_check or _("Unknown")}</span></strong></p>
    </div>

    <div class="report-section overview">
        <table>
            <tr>
                <th colspan="2">${_("Satellite")}</th>
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
                <td>${health}</td>
                <td><b>${sat_name}</b></td>
                <td>${h.hsize(current_sat.get('bitrate', 0), unit='bps', step=1000)}</td>
                <td>${current_sat.get('clients', 0)}</td>
            </tr>
            % endfor
        </table>
    </div>
</div>
</%block>
