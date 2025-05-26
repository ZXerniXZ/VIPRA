import Badge from 'react-bootstrap/Badge';
import 'bootstrap/dist/css/bootstrap.min.css';

function LogText({ip}) {
  return (
    <div>
      <h1>
        Test IP server mqqt <Badge bg="secondary">{ip}</Badge>
      </h1>
    </div>
  );
}

export default LogText;