import React from 'react';

function Result() {
    const raw = localStorage.getItem("resultData");
    const data = raw ? JSON.parse(raw) : null;

    if (!data) {
    return <div>잘못된 접근입니다.</div>;
    }

    return (
        <>
            <h1>결과 페이지</h1>
            <pre>{JSON.stringify(data, null, 2)}</pre>
        </>
    );
}

export default Result;