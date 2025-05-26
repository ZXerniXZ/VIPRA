import React from 'react'
import Button from 'react-bootstrap/Button';
import IPCheckFunction from './IPCheckFunction'

const ButtonCheck = () => {
    function checkIP() {
        <IPCheckFunction/>
    }
    return (
        <div>
            <Button variant="outline-success" onclick="checkIP()">Effettua un test!</Button>
        </div>
    )
}

export default ButtonCheck