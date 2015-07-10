<%inherit file='base.tpl'/>

<%block name="main">
<div class="h-bar">
    <h2>${_('Outernet Service Status')}</h2>
</div>
<div class="full-page-form status">
    <div class="report-section overview">
        <p><strong>${_("Updated")}:</strong>&nbsp;<span>${last_check or _("Unknown")}</span></p>
        <table>
            <tr>
                <th>${_("Satellite")}</th>
                <th>${_("Status")}</th>
                <th>${_("Error Rate")}</th>
                <th>${_("Average Bitrate")}</th>
            </tr>
            % for sat_id, sat_name in satellites.items():
            <tr>
                <% current_sat = status.get(sat_id, {}) %>
                % if current_sat:
                    % if current_sat['error']:
                    <% health = h.SPAN('', _class='health bad') %>
                    % elif current_sat['bitrate'] < bitrate_threshold or current_sat['error_rate'] < error_rate_threshold:
                    <% health = h.SPAN('', _class='health warning') %>
                    % else:
                    <% health = h.SPAN('', _class='health good') %>
                    % endif
                % else:
                    <% health = h.SPAN('', _class='health neutral') %>
                % endif
                <td>${sat_name}</td>
                <td>${health}</td>
                <td>${current_sat.get('error_rate', 0)}</td>
                <td>${current_sat.get('bitrate', 0)}</td>
            </tr>
            % endfor
        </table>
    </div>
    <div class="report-section error-log">
        <p><strong>${_("Error log")}:</strong></p>
        <ul>
        % for sat_status in status.values():
            % for err in sat_status.get('error', []):
            <li>${err}</li>
            % endfor
        % endfor
        </ul>
    </div>
</div>
</%block>
