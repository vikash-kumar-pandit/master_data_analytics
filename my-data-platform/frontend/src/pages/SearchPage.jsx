import React from 'react';
import DashboardLayout from '../DashboardLayout';
import useDataStore from '../store';
import SearchAndExport from '../components/SearchAndExport';

export default function SearchPage() {
  const { rawData, cleanedData, analysis } = useDataStore();
  const currentDataset = cleanedData.length > 0 ? cleanedData : rawData;

  return (
    <DashboardLayout>
      <SearchAndExport 
        rows={currentDataset} 
        analysis={analysis} 
      />
    </DashboardLayout>
  );
}
