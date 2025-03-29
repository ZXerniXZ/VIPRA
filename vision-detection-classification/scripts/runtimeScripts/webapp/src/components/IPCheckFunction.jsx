import React from 'react'
import BootstrapButton from 'react-bootstrap/Button';
import 'bootstrap/dist/css/bootstrap.min.css';

const ButtonCheck = () => {
    const [status, setStatus] = React.useState(null);

    const checkIP = async () => {
        try {
            const response = await fetch('http://142.250.180.132', {
                method: "HEAD", 
                mode: "no-cors" 
            });
            setStatus(true);
        } catch (error) {
            setStatus(false);
        }
    }

    return (
        <div>
            <BootstrapButton variant="outline-success" onClick={checkIP}>
                Effettua un test!
            </BootstrapButton>
            {status !== null && (
                <p className="mt-2">
                    Stato: {status ? "Raggiungibile ✅" : "Non raggiungibile ❌"}
                </p>
            )}
        </div>
    )
}

export default ButtonCheck