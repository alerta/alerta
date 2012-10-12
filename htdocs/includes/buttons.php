     <table width="100%">
        <td>
        <table class="table table-bordered table-condensed" id="status-counts">
          <tbody>
          <tr id="Alert-status" class="status">
            <td><span class="label">OPEN</span></td>
            <td id="alert-open">0</td>
            <td><span class="label">ACK</span></td>
            <td id="alert-ack">0</td>
            <td><span class="label">CLOSED</span></td>
            <td id="alert-closed">0</td>
          </tr>
          </tbody>
        </table>
      </td><td>
        <div align="right">
        <select id="limit-select" class="btn" name="limit" onchange="updateLimit(this.value)">
          <option value="0">No limit</option>
          <option value="100">Only 100</option>
          <option value="500">Only 500</option>
          <option value="1000">Only 1000</option>
          <option value="5000">Only 5000</option>
        </select>
        <select id="from-date-select" class="btn" name="last" onchange="updateFromDate(this.value)">
          <option value="0">All alerts</option>
          <option value="120">Last 2 minutes</option>
          <option value="300">Last 5 minutes</option>
          <option value="600">Last 10 minutes</option>
          <option value="1800">Last 30 minutes</option>
          <option value="3600">Last 1 hour</option>
        </select>
        <button class="btn" id="toggle-ACK" class="toggle-ACK"><span><i class="icon-minus"></i> Hide</span><span class="initially-hidden"><i class="icon-plus"></i> Show</span> Acknowledged</button>
        <button class="btn" id="toggle-NORMAL" class="toggle-NORMAL"><span><i class="icon-minus"></i> Hide</span><span class="initially-hidden"><i class="icon-plus"></i> Show</span> Normals</button>
        <button id="refresh-all" class="console-button btn"><i class="icon-refresh"></i> Refresh Now</button>
        </div>
      </td>
      </table>
