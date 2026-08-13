import { useState } from 'react';
import {
    Box,
    Table,
    TableHead,
    TableBody,
    TableRow,
    TableCell,
    Button,
} from '@mui/material';
import axios from 'axios';
import { API_BASE_URL } from './config';

const endpointMapping = {
    'Notion': 'notion/load',
    'Airtable': 'airtable/load',
    'HubSpot': 'hubspot/get_hubspot_items',
};

export const DataForm = ({ integrationType, credentials }) => {
    const [loadedData, setLoadedData] = useState(null);
    const endpoint = endpointMapping[integrationType];

    const handleLoad = async () => {
        try {
            const formData = new FormData();
            formData.append('credentials', JSON.stringify(credentials));
            const response = await axios.post(`${API_BASE_URL}/integrations/${endpoint}`, formData);
            const data = response.data;
            console.log(data)
            setLoadedData(Array.isArray(data) ? data : [data]);
        } catch (e) {
            alert(e?.response?.data?.detail);
        }
    }

    const columns = loadedData
        ? [...new Set(loadedData.flatMap((row) => Object.keys(row || {})))]
        : [];

    const formatValue = (value) => {
        if (value === null || value === undefined) return '';
        if (typeof value === 'object') return JSON.stringify(value);
        return String(value);
    }

    return (
        <Box display='flex' justifyContent='center' alignItems='center' flexDirection='column' width='100%'>
            <Box display='flex' flexDirection='column' alignItems='center' width='100%'>
                {loadedData && (
                    <Table sx={{ mt: 2, border: 1, borderColor: 'grey.300' }} size='small'>
                        <TableHead>
                            <TableRow>
                                {columns.map((col) => (
                                    <TableCell key={col} sx={{ fontWeight: 'bold' }}>{col}</TableCell>
                                ))}
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {loadedData.map((row, i) => (
                                <TableRow key={i}>
                                    {columns.map((col) => (
                                        <TableCell key={col}>{formatValue(row[col])}</TableCell>
                                    ))}
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
                <Button
                    onClick={handleLoad}
                    sx={{mt: 2}}
                    variant='contained'
                >
                    Load Data
                </Button>
                <Button
                    onClick={() => setLoadedData(null)}
                    sx={{mt: 1}}
                    variant='contained'
                >
                    Clear Data
                </Button>
            </Box>
        </Box>
    );
}