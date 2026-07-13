import React from 'react';
import DashboardLayout from '../DashboardLayout';
import useDataStore from '../store';
import GraphGallery from '../components/GraphGallery';

export default function GraphsPage() {
  const { rawData, cleanedData, analysis, domainData } = useDataStore();
  const currentDataset = cleanedData.length > 0 ? cleanedData : rawData;

  return (
    <DashboardLayout>
      <GraphGallery 
        rows={currentDataset} 
        analysis={analysis} 
        domainData={domainData} 
      />
    </DashboardLayout>
  );
}
