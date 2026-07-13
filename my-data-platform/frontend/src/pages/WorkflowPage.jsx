import React from 'react';
import DashboardLayout from '../DashboardLayout';
import useDataStore from '../store';
import WorkflowBuilder from '../components/WorkflowBuilder';

export default function WorkflowPage() {
  const { rawData, cleanedData, columns } = useDataStore();
  const currentDataset = cleanedData.length > 0 ? cleanedData : rawData;

  return (
    <DashboardLayout>
      <WorkflowBuilder 
        rows={currentDataset} 
        targetOptions={columns} 
      />
    </DashboardLayout>
  );
}
